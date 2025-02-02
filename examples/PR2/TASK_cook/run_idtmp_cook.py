from itertools import islice
from IPython import embed
import os, sys, time, re
import pickle
from prompt_toolkit.filters import app
from motion.motion_planners.utils import take
from plan_cache import PlanCache

import tmsmt as tm
import numpy as np
from codetiming import Timer
from copy import deepcopy

from pddl_parse.PDDL import PDDL_Parser
import pybullet as p
import pybullet_tools.utils as pu
import pybullet_tools.kuka_primitives3 as pk
import pybullet_tools.pr2_primitives as pp
import pybullet_tools.pr2_utils as ppu
from build_scenario import PlanningScenario
from task_planner import TaskPlanner
# from pybullet_manipulator import *

from logging_utils import *
logging.setLoggerClass(ColoredLogger)
logger = logging.getLogger('MAIN')

EPSILON = 0.01
RESOLUTION = 0.1
MOTION_ITERATION = 200

class DomainSemantics(object):
    def __init__(self, scene):
        self.scn = scene
        self.robot = self.scn.robots[0]
        self.arm = 'left'

        self.base_joints = [0,1,2]
        self.arm_joints = list(pp.get_arm_joints(self.robot, self.arm))
        self.movable_joints = self.base_joints + self.arm_joints

        self.all_bodies = self.scn.all_bodies
        self.max_distance = pp.MAX_DISTANCE
        self.self_collision = False
        self.approach_pose = (( -0.02 ,  0. , 0), (0.0, 0.0, 0.0, 1.0))
        self.ik_fn = pp.get_ik_fn(self.scn)
        # self.ir_sampler = pp.get_ir_sampler(self.scn)
        self.end_effector_link = pp.get_gripper_link(self.robot, self.arm)
        self.base_motion_obstacles = list(set(self.scn.env_bodies) | set(self.scn.regions))
        self.arm_motion_obstacles = list(set(self.scn.env_bodies) | set(self.scn.regions))
        self.obstacles = self.scn.env_bodies
        self.custom_limits = []

        self.base_lower_limits, self.base_upper_limits = pp.get_custom_limits(self.robot, self.base_joints, self.custom_limits)
        self.arm_joints_limits = pp.get_custom_limits(self.robot, self.arm_joints, self.custom_limits)
        self.arm_lower_limits, self.arm_upper_limits = self.arm_joints_limits

        self.disabled_collision_pairs={}
        self.sample_fn = pp.get_sample_fn(self.robot, self.arm_joints)
        self.arm_link = pp.get_gripper_link(self.robot, self.arm)
        self.arm_joints = pp.get_arm_joints(self.robot, self.arm)

        # subrobot - left arm with 7 joints
        self.selected_links = pu.get_link_subtree(self.robot, self.arm_joints[0])  # TODO: child_link_from_joint?
        self.selected_movable_joints = pu.prune_fixed_joints(self.robot, self.selected_links)
        self.selected_target_link = self.selected_links.index(self.arm_link)
        self.sub_robot = pu.clone_body(self.robot, links=self.selected_links, visual=False, collision=False)  # TODO: joint limits
        self.sub_movable_joints = pu.get_movable_joints(self.sub_robot)

    def plan_base_motion(self, goal_conf, obstacles, attachment=[]):
        raw_path = pp.plan_joint_motion(self.robot, self.base_joints, goal_conf, attachments=attachment,
                                obstacles=obstacles, custom_limits=self.custom_limits,
                                self_collisions=pp.SELF_COLLISIONS,
                                restarts=4, iterations=50, smooth=50)
        if raw_path is None:
            return False, None
        return True, raw_path

    def plan_arm_motion(self, goal_conf, obstacles, attachment=[]):
        raw_path = pp.plan_joint_motion(self.robot, self.arm_joints, goal_conf, obstacles=obstacles, self_collisions=self.self_collision, 
            disabled_collisions=self.disabled_collision_pairs, attachments=attachment,
            max_distance=self.max_distance, iterations=MOTION_ITERATION)
        if raw_path is None:
            return False, None
        return True, raw_path

    def get_arm_IK(self, goal_pose, max_iteration=20):
        init_conf = pu.get_joint_positions(self.robot, self.arm_joints)
        res, ik = False, None
        for _ in range(max_iteration):
            sub_kinematic_conf = pu.inverse_kinematics_helper(self.sub_robot, self.selected_target_link, goal_pose)
            # print(sub_kinematic_conf)
            pu.set_joint_positions(self.sub_robot, self.sub_movable_joints, sub_kinematic_conf)
            if pu.is_pose_close(pu.get_link_pose(self.sub_robot, self.selected_target_link), goal_pose):
                pu.set_joint_positions(self.robot, self.selected_movable_joints, sub_kinematic_conf)
                ik = pu.get_joint_positions(self.robot, self.arm_joints)
                if not pu.all_between(self.arm_lower_limits, ik, self.arm_upper_limits):
                    # print(f"IK ARM: ik of goal pose not in joint limits")
                    pu.set_joint_positions(self.robot, self.arm_joints, init_conf)
                    return False, None
                res = True
                break
        return res, ik

    def linear_interpolation(self, arr1, arr2, num=10):
        arrs = np.linspace(arr1, arr2, num)
        return [tuple(arr) for arr in arrs]

    def motion_plan(self, body, goal_pose, attaching=False):

        # attachment
        if attaching:
            body_pose = pu.get_pose(body)
            tcp_pose = pu.get_link_pose(self.robot, self.end_effector_link)
            grasp_pose = pu.multiply(pu.invert(tcp_pose), body_pose)
            # grasp = pk.BodyGrasp(body, grasp_pose, self.approach_pose, self.robot, attach_link=self.end_effector_link)
            obstacles = list(set(self.scn.all_bodies) - {body})
            # attachment = [grasp.attachment()]
            attachment = [pu.Attachment(self.robot, self.end_effector_link, grasp_pose, body)]
        else:
            obstacles = self.scn.all_bodies
            attachment = []

        arm_init_conf = pp.get_joint_positions(self.robot, self.arm_joints)
        start_pose = pu.get_link_pose(self.robot, self.end_effector_link)
        deapproach_pose = pu.multiply(start_pose, ((-0.1,0,0),(0,0,0,1)))
        pu.draw_pose(deapproach_pose)
        res, deapproach_conf = self.get_arm_IK(deapproach_pose, max_iteration=20)
        if not res:
            return False, None
        init_conf = pp.get_joint_positions(self.robot, self.movable_joints)

        self.base_collision_fn = pu.get_collision_fn(self.robot, self.base_joints, obstacles, attachment, self.self_collision, self.disabled_collision_pairs,
                                    custom_limits=self.custom_limits, max_distance=self.max_distance)
        self.arm_collision_fn = pu.get_collision_fn(self.robot, self.arm_joints, obstacles, attachment, self.self_collision, self.disabled_collision_pairs,
                                    custom_limits=self.custom_limits, max_distance=self.max_distance)

        # pu.draw_pose(goal_pose)
        goal_pose = pu.multiply(goal_pose, ((0,0,0),pu.quat_from_axis_angle((0,1,0),-np.pi/2)))
        goal_pose = pu.multiply(goal_pose, ((0,0,0),pu.quat_from_axis_angle((1,0,0),np.pi/2)))
        approach_pose = pu.multiply(goal_pose, ((-0.1,0,0),(0,0,0,1)))
        pu.draw_pose(goal_pose)
        pu.draw_pose(approach_pose)
        pu.draw_pose(((0,0,0),(0,0,0,1)), length=1)
        base_conf_generator = pp.learned_pose_generator(self.robot, goal_pose, arm='left',grasp_type='top')
        # get base and arm conf
        for base_conf in islice(base_conf_generator, 100):
            # find ik of base
            if not pu.all_between(self.base_lower_limits, base_conf, self.base_upper_limits):
                print(f"IK BASE: not in joint limits")
                pu.set_joint_positions(self.robot, self.movable_joints, init_conf)
                continue
            if self.base_collision_fn(base_conf):
                print(f"IK BASE: collision checked")
                pu.set_joint_positions(self.robot, self.movable_joints, init_conf)
                continue
            pu.set_joint_positions(self.robot, self.base_joints, base_conf)

            # find arm ik of goal pose
            self.sub_robot = pu.clone_body(self.robot, links=self.selected_links, visual=False, collision=False)  # TODO: joint limits
            res, arm_goal_conf = self.get_arm_IK(goal_pose, max_iteration=20)
            if (not res):
                print(f"IK ARM: no ik found")
                pu.set_joint_positions(self.robot, self.movable_joints, init_conf)
                continue

            # find arm ik of approach pose
            res, arm_approach_conf = self.get_arm_IK(approach_pose, max_iteration=20)
            if (not res):
                print(f"IK ARM: no ik found")
                pu.set_joint_positions(self.robot, self.movable_joints, init_conf)
                continue

            pu.set_joint_positions(self.robot, self.movable_joints, init_conf)
            # motion planning of base
            res, tmp_base_path = self.plan_base_motion(base_conf, obstacles, attachment)
            if not res:
                print(f"PLAN BASE: failed")
                pu.set_joint_positions(self.robot, self.movable_joints, init_conf)
                continue
            pu.set_joint_positions(self.robot, self.base_joints, base_conf)

            # motion planning of arm
            res, tmp_arm_path = self.plan_arm_motion(arm_approach_conf, obstacles, attachment)
            if res:
                base_path = pk.BodyPath(self.robot, tmp_base_path, self.base_joints, attachments=attachment)
                arm_path = pk.BodyPath(self.robot, self.linear_interpolation(arm_init_conf, tmp_arm_path[0])+tmp_arm_path+self.linear_interpolation(tmp_arm_path[-1], arm_goal_conf), self.arm_joints, attachments=attachment)
                pu.set_joint_positions(self.robot, self.base_joints, base_conf)
                pu.set_joint_positions(self.robot, self.arm_joints, arm_goal_conf)
                for a in attachment:
                    a.assign()

                print(f"found ik and valid path finally")
                return True, [base_path, arm_path]
            else:
                print(f"PLAN ARM: failed")

        else:
            print(f"no valid ik or path found")
            return False, None

class UnpackDomainSemantics(DomainSemantics):
    def activate(self):
        tm.bind_refine_operator(self.op_pick_up, "pick-up")
        tm.bind_refine_operator(self.op_put_down, "put-down")
        tm.bind_refine_operator(self.op_cook_or_clean, 'cook')
        tm.bind_refine_operator(self.op_cook_or_clean, 'clean')

    def op_pick_up(self, args):
        [a, obj, region, i, j] = args
        nop = tm.op_nop(self.scn)
        body = self.scn.bd_body[obj]
        (point, rotation) = pu.get_pose(body)
        center = pu.get_aabb_center(pu.get_aabb(body))
        extend = pu.get_aabb_extent(pu.get_aabb(body))
        x = center[0]
        y = center[1]
        z = center[2] + extend[2]/2
        body_pose = pu.Pose([x,y,z], pu.euler_from_quat(rotation))
        goal_pose = pu.multiply(body_pose, ((0,0,0), pu.quat_from_axis_angle([1,0,0],np.pi)))
        res, path = self.motion_plan(body, goal_pose, attaching=False)
        return res, path

    def op_put_down(self, args):
        (a, obj, region, i, j) = args
        nop = tm.op_nop(self.scn)
        body = self.scn.bd_body[obj]
        region_ind = self.scn.bd_body[region]

        aabb = pu.get_aabb(region_ind)
        center_region = pu.get_aabb_center(aabb)
        extend_region = pu.get_aabb_extent(aabb)

        (point, rotation) = pu.get_pose(body)
        aabb_body = pu.get_aabb(body)
        extend_body = pu.get_aabb_extent(aabb_body)
        x = center_region[0] + int(i)*RESOLUTION
        y = center_region[1] + int(j)*RESOLUTION
        z = center_region[2] + extend_region[2]/2 + extend_body[2] + EPSILON
        
        body_pose = pu.Pose([x,y,z], pu.euler_from_quat(rotation))
        goal_pose = pu.multiply(body_pose, ((0,0,0), pu.quat_from_axis_angle([1,0,0],np.pi)))

        res, path = self.motion_plan(body, goal_pose, attaching=True)
        return res, path

    def op_cook_or_clean(self, args):
        [a, obj, region, i, j] = args
        color = p.getVisualShapeData(self.scn.bd_body[region])[0][-1]
        p.changeVisualShape(self.scn.bd_body[obj], -1, rgbaColor=color)
        return True, obj

class PDDLProblem(object):
    def __init__(self, scene, domain_name):
        self.scn = scene
        self.domain_name = domain_name
        self.name = 'clean-and-cook'
        self.objects = None
        self.init = None
        self.goal = None
        self.metric = None

        self.objects = self._gen_scene_objects()
        self._goal_state()
        self._init_state()
        logger.info(f"problem instantiated")

    def _gen_scene_objects(self):
        scene_objects = dict()
        
        # define stove, sink, locations
        stove = set()
        sink = set()
        locations = set()
        for region in self.scn.regions:
            (lower, upper) = pu.get_aabb(region)
            size = np.abs((upper - lower)[:2])
            xr = int(np.floor(size[0]/2/RESOLUTION))
            yr = int(np.floor(size[1]/2/RESOLUTION))
            for i in range(xr+1):
                for j in range(yr+1):
                    locations.add(tm.mangle(self.scn.bd_body[region], i, j))
                    locations.add(tm.mangle(self.scn.bd_body[region], -i, j))
                    locations.add(tm.mangle(self.scn.bd_body[region], i, -j))
                    locations.add(tm.mangle(self.scn.bd_body[region], -i, -j))
        scene_objects['location'] = locations

        # define movable objects
        movable = set()
        for b in self.scn.movable_bodies:
            movable.add(self.scn.bd_body[b])
        scene_objects['block'] = movable

        return scene_objects

    def _init_state(self):

        init = []
        # handempty
        init.append(['handempty'])

        movables = self.scn.movable_bodies

        # ontable
        region_aabb=dict()
        for r in self.scn.regions:
            region_aabb[self.scn.bd_body[r]] = np.array(pu.get_aabb(r))[:,:2]
        occuppied = set()
        for m in movables:
            point = np.array(pu.get_point(m))[:2]
            for region, aabb in region_aabb.items():
                if pu.aabb_contains_point(point, aabb):
                    loc = (point - np.array(pu.get_point(self.scn.bd_body[region]))[:2])/RESOLUTION
                    location = tm.mangle(region, int(loc[0]), int(loc[1]))
                    init.append(['ontable', self.scn.bd_body[m], location])
                    occuppied.add(location)
                    break
        # clear
        for l in list(self.objects['location']):
            if l not in occuppied:
                init.append(['clear',l])
            else:
                init.append(['not',['clear',l]])

        # holding
        for m in movables:
            init.append(['not',['holding', self.scn.bd_body[m]]])

        # cleaned
        for m in movables:
            init.append(['not',['cleaned', self.scn.bd_body[m]]])

        # cooked
        for m in movables:
            init.append(['not', ['cooked', self.scn.bd_body[m]]])
        
        # issink and isstove
        for loc in self.objects['location']:
            if 'stove' in loc:
                init.append(['isstove', loc])
            if 'sink' in loc:
                init.append(['issink', loc])

        self.init = init

    def _goal_state(self):
        self.goal = []
        self.goal.append(['handempty'])
        self.goal.append(['cooked', 'box1'])
        self.goal.append(['cooked', 'box2'])
        self.goal.append(['cooked', 'box3'])
        self.goal.append(['cooked', 'box4'])
        # self.goal.append(['cooked', 'box5'])
        # self.goal.append(['cooked', 'box6'])
        # self.goal.append(['cooked', 'box7'])
        # self.goal.append(['cooked', 'box8'])
        # self.goal.append(['cooked', 'box9'])
        # ontable = ['or']
        # for loc in self.objects['location']:
        #     if 'region2' in loc:
        #         ontable.append(['ontable','c1',loc])

def ExecutePlanNaive(scn, task_plan, motion_plan, speed=0.01):
    robot = scn.robots[0]
    ind = -1
    for _,tp in task_plan.items():
        print(tp)
        ind += 1
        tp_list = re.split(' |__', tp[1:-1])
        if 'put-down' == tp_list[0] or 'pick-up' == tp_list[0]:
            cmd = pk.Command(motion_plan[ind])
            cmd.execute(time_step=speed)
        else:
            [a, body, region, i,j] = tp_list
            target_color = p.getVisualShapeData(scn.bd_body[region])[0][-1]
            body_color = p.getVisualShapeData(scn.bd_body[body])[0][-1]
            colors = np.linspace(body_color, target_color, 10)
            for c in colors:
                pu.set_color(scn.bd_body[body], c)
                time.sleep(0.1)
    time.sleep(1)
    scn.reset()

def SetState(scn, task_plan, motion_plan):
    robot = scn.robots[0]
    ind = -1
    for _,tp in task_plan.items():
        ind += 1
        if ind>=len(motion_plan):
            break
        path = [motion_plan[ind][0], motion_plan[ind][-1]]
        tp_list = re.split(' |__', tp[1:-1])
        if 'put-down' == tp_list[0] or 'pick-up' == tp_list[0]:

            cmd = pk.Command(path)
            cmd.execute(time_step=0.0001)
        else:
            [a, body, region, i,j] = tp_list
            target_color = p.getVisualShapeData(scn.bd_body[region])[0][-1]
            body_color = p.getVisualShapeData(scn.bd_body[body])[0][-1]
            colors = np.linspace(body_color, target_color, 10)
            for c in colors:
                pu.set_color(scn.bd_body[body], c)

def main(visualization=True):
    tp_total_time = Timer(name='tp_total_time', text='', logger=logger.info)
    mp_total_time = Timer(name='mp_total_time', text='', logger=logger.info)
    total_time = 0

    pu.connect(use_gui=visualization)
    scn = PlanningScenario()
    parser = PDDL_Parser()
    dirname = os.path.dirname(os.path.abspath(__file__))
    domain_filename = os.path.join(dirname, 'domain_idtmp_cook.pddl')
    parser.parse_domain(domain_filename)
    domain_name = parser.domain_name
    problem_filename = os.path.join(dirname, 'problem_idtmp_'+domain_name+'.pddl')
    problem = PDDLProblem(scn, parser.domain_name)
    parser.dump_problem(problem, problem_filename)
    logger.info(f"problem.pddl dumped")
    # initial domain semantics
    domain_semantics = UnpackDomainSemantics(scn)
    domain_semantics.activate()

    # IDTMP
    tp_total_time.start()
    tp = TaskPlanner(problem_filename, domain_filename, start_horizon=29, max_horizon=40)
    tp.incremental()
    tp.modeling()
    tp_total_time.stop()
    tm_plan = None
    t00 = time.time()
    while tm_plan is None:
        # ------------------- task plan ---------------------
        t0 = time.time()
        t_plan = None
        while t_plan is None:
            t_plan = tp.search_plan()
            if t_plan is None:
                logger.warning(f"task plan not found in horizon: {tp.horizon}")
                print(f'')
                # if tp.horizon<19:
                num_constraints = 0
                for k, v, in tp.formula.items():
                    if k != 'goal':
                        num_constraints += len(v)
                print(f'ground_actions: {len(tp.encoder.action_variables)*len(tp.encoder.action_variables[0])}')
                print(f'ground_states: {len(tp.encoder.boolean_variables)*len(tp.encoder.boolean_variables[0])}')
                print(f'number_constraints: {num_constraints}')
                # else:
                #     embed()
                tp_total_time.start()
                tp.incremental()
                tp.modeling()

                tp_total_time.stop()
                logger.info(f"search task plan in horizon: {tp.horizon}")
                # global MOTION_ITERATION
                # MOTION_ITERATION += 10
                print(f"all timers: {tp_total_time.timers}")
                
        logger.info(f"task plan found, in horizon: {tp.horizon}")
        for h,p in t_plan.items():
            logger.info(f"{h}: {p}")

        # ------------------- motion plan ---------------------
        mp_total_time.start()
        res, m_plan = tm.motion_refiner(t_plan)
        mp_total_time.stop()

        scn.reset()
        if res:
            logger.info(f"task and motion plan found")
            break
        else: 
            t0 = time.time()
            logger.warning(f"motion refine failed")
            logger.info(f'')
            tp.add_constraint(m_plan)
            t_plan = None

    total_time = time.time()-t00
    all_timers = tp_total_time.timers
    print(f"all timers: {all_timers}")
    print("task plan time: {:0.4f} s".format(all_timers[tp_total_time.name]))
    print("motion refiner time: {:0.4f} s".format(all_timers[mp_total_time.name]))
    print(f"total planning time: {total_time}")
    print(f"task plan counter: {tp.counter}")

    while True:
        ExecutePlanNaive(scn, t_plan, m_plan)
        time.sleep(1)

    pu.disconnect()

def sim_plancache():
    task_planning_timer = Timer(name='task_planning_time', text='')
    motion_planning_timer = Timer(name='motion_planning_time', text='')
    total_planning_timer = Timer(name='total_planning_time', text='')

    task_planning_timer.reset()
    total_planning_timer.reset()
    motion_planning_timer.reset()

    pu.connect(use_gui=visualization)
    scn = PlanningScenario()
    parser = PDDL_Parser()
    dirname = os.path.dirname(os.path.abspath(__file__))
    domain_filename = os.path.join(dirname, 'domain_idtmp_cook.pddl')
    parser.parse_domain(domain_filename)
    domain_name = parser.domain_name
    problem_filename = os.path.join(dirname, 'problem_idtmp_'+domain_name+'.pddl')
    problem = PDDLProblem(scn, parser.domain_name)
    parser.dump_problem(problem, problem_filename)
    print(f"problem.pddl dumped")
    # initial domain semantics
    domain_semantics = UnpackDomainSemantics(scn)
    domain_semantics.activate()

    # IDTMP
    total_planning_timer.start()
    task_planning_timer.start()
    tp = TaskPlanner(problem_filename, domain_filename, start_horizon=11, max_horizon=100)
    tp.incremental()
    tp.modeling()
    task_planning_timer.stop()
    tm_plan = None
    t00 = time.time()
    path_cache = PlanCache()
    tamp_timeout = 1000
    while tm_plan is None and time.time()-t00<tamp_timeout:
        # ------------------- task plan ---------------------
        t0 = time.time()
        t_plan = None
        while t_plan is None:
            task_planning_timer.start()
            t_plan = tp.search_plan()
            task_planning_timer.stop()
            if t_plan is None:
                print(f"task plan not found in horizon: {tp.horizon}")
                print(f'')
                # if tp.horizon<19:
                num_constraints = 0
                for k, v, in tp.formula.items():
                    if k != 'goal':
                        num_constraints += len(v)
                print(f'ground_actions {len(tp.encoder.action_variables)*len(tp.encoder.action_variables[0])}')
                print(f'ground_states {len(tp.encoder.boolean_variables)*len(tp.encoder.boolean_variables[0])}')
                print(f'number_constraints {num_constraints}')
                print(f"task planning time: {task_planning_timer.timers['task_planning_time']}")
                # else:
                #     embed()
                task_planning_timer.start()
                if not tp.incremental():
                    task_planning_timer.stop()
                    print(f"{tp.max_horizon} exceeding, TAMP is failed")
                    return False
                tp.modeling()
                task_planning_timer.stop()
                print(f"search task plan in horizon: {tp.horizon}")
                # global MOTION_ITERATION
                # MOTION_ITERATION += 10
        # print(f"all timers: {task_planning_timer.timers}")
        embed()
        print(f"task plan found, in horizon: {tp.horizon}")
        for h,p in t_plan.items():
            logger.info(f"{h}: {p}")

        # ------------------- motion plan ---------------------
        motion_planning_timer.start()
        depth, prefix_m_plans = path_cache.find_plan_prefixes(list(t_plan.values()))
        if depth>=0:
            t_plan_to_validate = deepcopy(t_plan)
            for _ in range(depth+1):
                t_plan_to_validate.pop(min(t_plan_to_validate.keys()))
            print('found plan prefixed')
            SetState(scn, t_plan, prefix_m_plans)
            res, post_m_plan, failed_step = tm.motion_refiner(t_plan_to_validate)
            m_plan = prefix_m_plans + post_m_plan
        else:
            res, m_plan, failed_step = tm.motion_refiner(t_plan)
        motion_planning_timer.stop()

        scn.reset()
        if res:
            logger.info(f"task and motion plan found")
            break
        else:
            path_cache.add_feasible_motion(list(t_plan.values()), m_plan)   
            logger.warning(f"motion refine failed")
            logger.info(f'')
            task_planning_timer.start()
            tp.add_constraint(failed_step, typ='general', cumulative=False)
            task_planning_timer.stop()
            t_plan = None

    if time.time()-t00>tamp_timeout:
        total_planning_timer.stop()
        print(f"{tamp_timeout} s Timeout, TAMP is failed")
        return False
    else:
        total_planning_timer.stop()
        all_timers = task_planning_timer.timers
        print(f"TAMP succeed")
        print(f"all timers: {all_timers}")
        print("task_planning_time {:0.4f} s".format(all_timers[task_planning_timer.name]))
        print("motion_refiner_time {:0.4f} s".format(all_timers[motion_planning_timer.name]))
        print("total_planning_time {:0.4f} s".format(all_timers[total_planning_timer.name]))
        print(f"final_visits {tp.counter}")

    pu.disconnect()

def multisim():
    task_planning_timer = Timer(name='task_planning_time', text='')
    motion_planning_timer = Timer(name='motion_planning_time', text='')
    total_planning_timer = Timer(name='total_planning_time', text='')
    total_time = 0

    pu.connect(use_gui=visualization)
    scn = PlanningScenario()
    parser = PDDL_Parser()
    dirname = os.path.dirname(os.path.abspath(__file__))
    domain_filename = os.path.join(dirname, 'domain_idtmp_cook.pddl')
    parser.parse_domain(domain_filename)
    domain_name = parser.domain_name
    problem_filename = os.path.join(dirname, 'problem_idtmp_'+domain_name+'.pddl')
    problem = PDDLProblem(scn, parser.domain_name)
    parser.dump_problem(problem, problem_filename)
    logger.info(f"problem.pddl dumped")
    # initial domain semantics
    domain_semantics = UnpackDomainSemantics(scn)
    domain_semantics.activate()

    for _ in range(max_sim):
        # IDTMP
        t00 = time.time()
        task_planning_timer.reset()
        total_planning_timer.reset()
        motion_planning_timer.reset()

        total_planning_timer.start()
        task_planning_timer.start()
        tp = TaskPlanner(problem_filename, domain_filename, start_horizon=0, max_horizon=14)
        tp.incremental()
        tp.modeling()
        task_planning_timer.stop()

        tm_plan = None
        while tm_plan is None:
            # ------------------- task plan ---------------------
            t0 = time.time()
            t_plan = None
            while t_plan is None:
                task_planning_timer.start()
                t_plan = tp.search_plan()
                if t_plan is None:
                    print(f"WARN: task plan not found in horizon: {tp.horizon}")
                    print(f'')
                    tp.incremental()
                    tp.modeling()
                    print(f"search task plan in horizon: {tp.horizon}")
                    # global MOTION_ITERATION 
                    # MOTION_ITERATION += 10
                task_planning_timer.stop()
            print(f"task plan found, in horizon: {tp.horizon}")
            for h,p in t_plan.items():
                print(f"{h}: {p}")

            # ------------------- motion plan ---------------------
            motion_planning_timer.start()
            res, m_plan = tm.motion_refiner(t_plan)
            motion_planning_timer.stop()

            scn.reset()
            if res:
                print(f"task and motion plan found")
                break
            else: 
                print(f"WARN: motion refine failed")
                logger.info(f'')
                tp.add_constraint(m_plan)
                t_plan = None
        total_planning_timer.stop()
        total_time = time.time()-t00
        all_timers = total_planning_timer.timers
        print(f"all timers: {all_timers}")
        print("task_planning_time {:0.4f} s".format(all_timers[task_planning_timer.name]))
        print("motion_refiner_time {:0.4f} s".format(all_timers[motion_planning_timer.name]))
        print("total_planning_time {:0.4f} s".format(all_timers[total_planning_timer.name]))
        print(f"final_visits {tp.counter}")

if __name__=="__main__":
    visualization = bool(int(sys.argv[1]))
    RESOLUTION = float(sys.argv[2])
    max_sim = int(sys.argv[3])
    MOTION_ITERATION = int(sys.argv[4])
    for _ in range(max_sim):
        sim_plancache()
