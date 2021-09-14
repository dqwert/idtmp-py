#!/usr/bin/env python

from __future__ import print_function
import numpy as np
import cProfile
import pstats
import argparse
import pickle as pk
import time
from etamp.actions import ActionInfo
from etamp.stream import StreamInfo
from utils.pybullet_tools.pr2_primitives import BodyPose, Conf, get_ik_ir_gen, get_motion_gen, \
    get_stable_gen, get_grasp_gen, Attach, Detach, Clean, Cook, control_commands, \
    get_gripper_joints, GripperCommand, apply_commands, State, Command, sdg_sample_place, \
    sdg_sample_grasp, sdg_ik_grasp, sdg_motion_base_joint
from utils.pybullet_tools.pr2_utils import get_arm_joints, ARM_NAMES, get_group_joints, get_group_conf
from utils.pybullet_tools.utils import WorldSaver, connect, get_pose, set_pose, get_configuration, is_placement, \
    disconnect, get_bodies, connect, get_pose, is_placement, point_from_pose, \
    disconnect, user_input, get_joint_positions, enable_gravity, save_state, restore_state, HideOutput, \
    get_distance, LockRenderer, get_min_limit, get_max_limit
from etamp.progressive3 import solve_progressive, solve_progressive2
from etamp.pddlstream.utils import read, INF, get_file_path, find_unique

from etamp.p_uct2 import PlannerUCT
from etamp.tree_node2 import ExtendedNode
from etamp.env_sk_branch import SkeletonEnv
from build_scenario import PlanningScenario


def get_fixed(robot, movable):
    rigid = [body for body in get_bodies() if body != robot]
    fixed = [body for body in rigid if body not in movable]
    return fixed


def place_movable(certified):
    placed = []
    for literal in certified:
        if literal[0] == 'not':
            fact = literal[1]
            if fact[0] == 'trajcollision':
                _, b, p = fact[1:]
                set_pose(b, p.pose)
                placed.append(b)
    return placed


def extract_motion(action_plan):
    """
    Return a list of robot motions
    each of which corresponds to a motor action in the action_plan.
    """
    list_motion = []
    for name, args, _ in action_plan:
        # args are instances of classes
        cmd = args[-1]
        if name == 'place':
            """Since 'place' is the reversed motion of 'pick',
               its path is simply the reverse of what generated by 'pick'."""
            reversed_cmd = cmd.reverse()
            list_motion += reversed_cmd.body_paths
        elif name in ['move', 'move_free', 'move_holding', 'pick']:
            list_motion += cmd.body_paths
    print('list of paths ----------------------------')
    print(action_plan)
    print(list_motion)
    print('----------------------------------')
    return list_motion


def move_cost_fn(*args):
    """
    :param c: Commands
    """
    c = args[-1]  # objects
    [t] = c.value.body_paths
    distance = t.distance()
    return distance + 0.1


def get_const_cost_fn(cost):
    def fn(*args):
        return cost

    return fn


def get_action_cost(plan):
    cost = None
    if plan:
        cost = 0
        for paction in plan:
            if callable(paction.pa_info.cost_fn):
                cost += paction.pa_info.cost_fn(*paction.args)
        # print('Action Cost ====================== ', cost)
    return cost


def get_update_env_reward_fn(scn, action_info):
    def get_actions_cost(exe_plan):
        cost = None
        if exe_plan:
            cost = 0
            for action in exe_plan:
                if action.name not in action_info:
                    continue
                cost_fn = action_info[action.name].cost_fn
                if callable(cost_fn):
                    cost += cost_fn(*action.parameters)
        return cost

    def fn(list_exe_action):

        cost = get_actions_cost(list_exe_action)

        """Execution uncertainty will be implemented here."""
        with LockRenderer():
            for action in list_exe_action:
                for patom in action.add_effects:
                    if patom.name.lower() == "AtBConf".lower():
                        body_config = patom.args[0].value
                        body_config.assign()
                    elif patom.name.lower() == "AtPose".lower():
                        body_pose = patom.args[1].value
                        body_pose.assign()
                    elif patom.name.lower() == "AtGrasp".lower():
                        body_grasp = patom.args[2].value
                        attachment = body_grasp.attachment(scn.pr2, scn.arm_left)
                        attachment.assign()

        if cost is False:
            return None

        return 0.1 * np.exp(-cost)

    return fn


def postprocess_plan(scn, exe_plan, teleport=False):
    if exe_plan is None:
        return None
    commands = []
    for i, (name, args) in enumerate(exe_plan):
        if name == 'move_base':
            c = args[-1]
            new_commands = c.commands
        elif name == 'pick':
            a, b, p, g, _, c = args
            [t] = c.commands
            close_gripper = GripperCommand(scn.robots[0], a, g.grasp_width, teleport=teleport)
            attach = Attach(scn.robots[0], a, g, b)
            new_commands = [t, close_gripper, attach, t.reverse()]
        elif name == 'place':
            a, b, p, g, _, c = args
            [t] = c.commands
            gripper_joint = get_gripper_joints(scn.robots[0], a)[0]
            position = get_max_limit(scn.robots[0], gripper_joint)
            open_gripper = GripperCommand(scn.robots[0], a, position, teleport=teleport)
            detach = Detach(scn.robots[0], a, b)
            new_commands = [t, detach, open_gripper, t.reverse()]
        elif name == 'clean':  # TODO: add text or change color?
            body, sink = args
            new_commands = [Clean(body)]
        elif name == 'cook':
            body, stove = args
            new_commands = [Cook(body)]
        elif name == 'press_clean':
            body, sink, arm, button, bq, c = args
            [t] = c.commands
            new_commands = [t, Clean(body), t.reverse()]
        elif name == 'press_cook':
            body, sink, arm, button, bq, c = args
            [t] = c.commands
            new_commands = [t, Cook(body), t.reverse()]
        else:
            raise ValueError(name)
        # print(i, name, args, new_commands)
        commands += new_commands
    return commands


def play_commands(commands):
    use_control = False
    if use_control:
        control_commands(commands)
    else:
        apply_commands(State(), commands, time_step=0.01)


#######################################################

def get_pddlstream_problem(scn):
    """"""

    robot = scn.robots[0]
    movable = scn.movable_bodies

    domain_pddl = read(get_file_path(__file__, 'pddl/domain.pddl'))
    stream_pddl = read(get_file_path(__file__, 'pddl/stream.pddl'))

    initial_bq = Conf(robot,
                      get_group_joints(robot, 'base'),
                      get_group_conf(robot, 'base'))
    init = [('CanMove',),
            ('CanOperate',),
            ('IsBConf', initial_bq),
            ('AtBConf', initial_bq),
            ]
    init += [('Sink', scn.bd_body['sink'])]
    init += [('Stove', scn.bd_body['stove'])]

    for arm in ARM_NAMES:
        # for arm in problem.arms:
        joints = get_arm_joints(robot, arm)
        conf = Conf(robot, joints, get_joint_positions(robot, joints))
        init += [('IsArm', arm), ('HandEmpty', arm)]
        if arm in scn.controllable:
            init += [('Controllable', arm)]

    fixed = get_fixed(robot, movable)
    all_bodies = list(set(movable) | set(fixed))
    for body in movable:
        pose = BodyPose(body, get_pose(body))
        init += [('Graspable', body), ('IsPose', body, pose),
                 ('AtPose', body, pose)]
        for surface in scn.regions:
            init += [('Stackable', body, surface)]
            if is_placement(body, surface):
                init += [('Supported', body, pose, surface)]

    goal = ('and',
            ('AtBConf', initial_bq),
            # ('On', scn.bd_body['box1'], scn.bd_body['table']),
            ('Cooked', scn.bd_body['box1']),
            ('Cooked', scn.bd_body['box2']),
            # ('Cooked', scn.bd_body['box3']),
            # ('Cooked', scn.bd_body['box4']),
            # ('Cooked', scn.bd_body['box5']),
            # ('Cooked', scn.bd_body['box6']),
            )

    stream_info = {'sample-place': StreamInfo(seed_gen_fn=sdg_sample_place(scn), every_layer=15,
                                             free_generator=True, discrete=False, p1=[1, 1, 1], p2=[.2, .2, .2]),
                   'sample-grasp': StreamInfo(seed_gen_fn=sdg_sample_grasp(scn)),
                   'inverse-kinematics': StreamInfo(seed_gen_fn=sdg_ik_grasp(scn)),
                   'plan-base-motion': StreamInfo(seed_gen_fn=sdg_motion_base_joint(scn)),
                   }

    action_info = {'move_base': ActionInfo(optms_cost_fn=get_const_cost_fn(5), cost_fn=get_const_cost_fn(5)),
                   'place': ActionInfo(optms_cost_fn=get_const_cost_fn(1), cost_fn=get_const_cost_fn(1)),
                   'pick': ActionInfo(optms_cost_fn=get_const_cost_fn(1), cost_fn=get_const_cost_fn(1)),
                   }

    return domain_pddl, stream_pddl, init, goal, stream_info, action_info


#######################################################

def main():
    visualization = 0
    connect(use_gui=visualization)

    scn = PlanningScenario()

    pddlstream_problem = get_pddlstream_problem(scn)
    _, _, _, _, stream_info, action_info = pddlstream_problem

    # pr = cProfile.Profile()
    # pr.enable()

    st = time.time()

    new_problem = 1
    if new_problem:
        sk_batch = solve_progressive2(pddlstream_problem,
                                      num_optms_init=80, target_sk=20)
        op_plan = sk_batch.generate_operatorPlan(3)  # 6
    else:
        with open('C_operatorPlans/C_op_sas.1.pk', 'rb') as f:
            op_plan = pk.load(f)

    e_root = ExtendedNode()
    assert op_plan is not None
    skeleton_env = SkeletonEnv(e_root.num_children, op_plan,
                               get_update_env_reward_fn(scn, action_info),
                               stream_info, scn)
    selected_branch = PlannerUCT(skeleton_env)

    concrete_plan = selected_branch.think(900, visualization)

    if concrete_plan is None:
        print('TAMP is failed.', concrete_plan)
        disconnect()
        return
    thinking_time = time.time() - st
    print('TAMP is successful. think_time: '.format(thinking_time))

    exe_plan = None
    if concrete_plan is not None:
        exe_plan = []
    for action in concrete_plan:
        exe_plan.append((action.name, [arg.value for arg in action.parameters]))

    with open('exe_plan.pk', 'wb') as f:
        pk.dump((scn, exe_plan), f)

    # pr.disable()
    # pstats.Stats(pr).sort_stats('tottime').print_stats(10)

    if exe_plan is None:
        disconnect()
        return

    disconnect()
    connect(use_gui=True)
    PlanningScenario()

    with LockRenderer():
        commands = postprocess_plan(scn, exe_plan)

    play_commands(commands)

    disconnect()

    print('Finished.')


if __name__ == '__main__':
    main()
