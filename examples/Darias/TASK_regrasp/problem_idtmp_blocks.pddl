;17:43:18 25/09

(define (problem regrasp-block)
   (:domain blocks)

   (:objects
          region_drawer__-1__-1 - location
          region_drawer__-1__-2 - location
          region_drawer__-1__0 - location
          region_drawer__-1__1 - location
          region_drawer__-1__2 - location
          region_drawer__-2__-1 - location
          region_drawer__-2__-2 - location
          region_drawer__-2__0 - location
          region_drawer__-2__1 - location
          region_drawer__-2__2 - location
          region_drawer__0__-1 - location
          region_drawer__0__-2 - location
          region_drawer__0__0 - location
          region_drawer__0__1 - location
          region_drawer__0__2 - location
          region_drawer__1__-1 - location
          region_drawer__1__-2 - location
          region_drawer__1__0 - location
          region_drawer__1__1 - location
          region_drawer__1__2 - location
          region_drawer__2__-1 - location
          region_drawer__2__-2 - location
          region_drawer__2__0 - location
          region_drawer__2__1 - location
          region_drawer__2__2 - location
          region_shelf__-1__-1 - location
          region_shelf__-1__-2 - location
          region_shelf__-1__-3 - location
          region_shelf__-1__-4 - location
          region_shelf__-1__-5 - location
          region_shelf__-1__0 - location
          region_shelf__-1__1 - location
          region_shelf__-1__2 - location
          region_shelf__-1__3 - location
          region_shelf__-1__4 - location
          region_shelf__-1__5 - location
          region_shelf__-2__-1 - location
          region_shelf__-2__-2 - location
          region_shelf__-2__-3 - location
          region_shelf__-2__-4 - location
          region_shelf__-2__-5 - location
          region_shelf__-2__0 - location
          region_shelf__-2__1 - location
          region_shelf__-2__2 - location
          region_shelf__-2__3 - location
          region_shelf__-2__4 - location
          region_shelf__-2__5 - location
          region_shelf__-3__-1 - location
          region_shelf__-3__-2 - location
          region_shelf__-3__-3 - location
          region_shelf__-3__-4 - location
          region_shelf__-3__-5 - location
          region_shelf__-3__0 - location
          region_shelf__-3__1 - location
          region_shelf__-3__2 - location
          region_shelf__-3__3 - location
          region_shelf__-3__4 - location
          region_shelf__-3__5 - location
          region_shelf__-4__-1 - location
          region_shelf__-4__-2 - location
          region_shelf__-4__-3 - location
          region_shelf__-4__-4 - location
          region_shelf__-4__-5 - location
          region_shelf__-4__0 - location
          region_shelf__-4__1 - location
          region_shelf__-4__2 - location
          region_shelf__-4__3 - location
          region_shelf__-4__4 - location
          region_shelf__-4__5 - location
          region_shelf__-5__-1 - location
          region_shelf__-5__-2 - location
          region_shelf__-5__-3 - location
          region_shelf__-5__-4 - location
          region_shelf__-5__-5 - location
          region_shelf__-5__0 - location
          region_shelf__-5__1 - location
          region_shelf__-5__2 - location
          region_shelf__-5__3 - location
          region_shelf__-5__4 - location
          region_shelf__-5__5 - location
          region_shelf__0__-1 - location
          region_shelf__0__-2 - location
          region_shelf__0__-3 - location
          region_shelf__0__-4 - location
          region_shelf__0__-5 - location
          region_shelf__0__0 - location
          region_shelf__0__1 - location
          region_shelf__0__2 - location
          region_shelf__0__3 - location
          region_shelf__0__4 - location
          region_shelf__0__5 - location
          region_shelf__1__-1 - location
          region_shelf__1__-2 - location
          region_shelf__1__-3 - location
          region_shelf__1__-4 - location
          region_shelf__1__-5 - location
          region_shelf__1__0 - location
          region_shelf__1__1 - location
          region_shelf__1__2 - location
          region_shelf__1__3 - location
          region_shelf__1__4 - location
          region_shelf__1__5 - location
          region_shelf__2__-1 - location
          region_shelf__2__-2 - location
          region_shelf__2__-3 - location
          region_shelf__2__-4 - location
          region_shelf__2__-5 - location
          region_shelf__2__0 - location
          region_shelf__2__1 - location
          region_shelf__2__2 - location
          region_shelf__2__3 - location
          region_shelf__2__4 - location
          region_shelf__2__5 - location
          region_shelf__3__-1 - location
          region_shelf__3__-2 - location
          region_shelf__3__-3 - location
          region_shelf__3__-4 - location
          region_shelf__3__-5 - location
          region_shelf__3__0 - location
          region_shelf__3__1 - location
          region_shelf__3__2 - location
          region_shelf__3__3 - location
          region_shelf__3__4 - location
          region_shelf__3__5 - location
          region_shelf__4__-1 - location
          region_shelf__4__-2 - location
          region_shelf__4__-3 - location
          region_shelf__4__-4 - location
          region_shelf__4__-5 - location
          region_shelf__4__0 - location
          region_shelf__4__1 - location
          region_shelf__4__2 - location
          region_shelf__4__3 - location
          region_shelf__4__4 - location
          region_shelf__4__5 - location
          region_shelf__5__-1 - location
          region_shelf__5__-2 - location
          region_shelf__5__-3 - location
          region_shelf__5__-4 - location
          region_shelf__5__-5 - location
          region_shelf__5__0 - location
          region_shelf__5__1 - location
          region_shelf__5__2 - location
          region_shelf__5__3 - location
          region_shelf__5__4 - location
          region_shelf__5__5 - location
          region_table__-1__-1 - location
          region_table__-1__-2 - location
          region_table__-1__-3 - location
          region_table__-1__-4 - location
          region_table__-1__-5 - location
          region_table__-1__0 - location
          region_table__-1__1 - location
          region_table__-1__2 - location
          region_table__-1__3 - location
          region_table__-1__4 - location
          region_table__-1__5 - location
          region_table__-2__-1 - location
          region_table__-2__-2 - location
          region_table__-2__-3 - location
          region_table__-2__-4 - location
          region_table__-2__-5 - location
          region_table__-2__0 - location
          region_table__-2__1 - location
          region_table__-2__2 - location
          region_table__-2__3 - location
          region_table__-2__4 - location
          region_table__-2__5 - location
          region_table__-3__-1 - location
          region_table__-3__-2 - location
          region_table__-3__-3 - location
          region_table__-3__-4 - location
          region_table__-3__-5 - location
          region_table__-3__0 - location
          region_table__-3__1 - location
          region_table__-3__2 - location
          region_table__-3__3 - location
          region_table__-3__4 - location
          region_table__-3__5 - location
          region_table__-4__-1 - location
          region_table__-4__-2 - location
          region_table__-4__-3 - location
          region_table__-4__-4 - location
          region_table__-4__-5 - location
          region_table__-4__0 - location
          region_table__-4__1 - location
          region_table__-4__2 - location
          region_table__-4__3 - location
          region_table__-4__4 - location
          region_table__-4__5 - location
          region_table__-5__-1 - location
          region_table__-5__-2 - location
          region_table__-5__-3 - location
          region_table__-5__-4 - location
          region_table__-5__-5 - location
          region_table__-5__0 - location
          region_table__-5__1 - location
          region_table__-5__2 - location
          region_table__-5__3 - location
          region_table__-5__4 - location
          region_table__-5__5 - location
          region_table__0__-1 - location
          region_table__0__-2 - location
          region_table__0__-3 - location
          region_table__0__-4 - location
          region_table__0__-5 - location
          region_table__0__0 - location
          region_table__0__1 - location
          region_table__0__2 - location
          region_table__0__3 - location
          region_table__0__4 - location
          region_table__0__5 - location
          region_table__1__-1 - location
          region_table__1__-2 - location
          region_table__1__-3 - location
          region_table__1__-4 - location
          region_table__1__-5 - location
          region_table__1__0 - location
          region_table__1__1 - location
          region_table__1__2 - location
          region_table__1__3 - location
          region_table__1__4 - location
          region_table__1__5 - location
          region_table__2__-1 - location
          region_table__2__-2 - location
          region_table__2__-3 - location
          region_table__2__-4 - location
          region_table__2__-5 - location
          region_table__2__0 - location
          region_table__2__1 - location
          region_table__2__2 - location
          region_table__2__3 - location
          region_table__2__4 - location
          region_table__2__5 - location
          region_table__3__-1 - location
          region_table__3__-2 - location
          region_table__3__-3 - location
          region_table__3__-4 - location
          region_table__3__-5 - location
          region_table__3__0 - location
          region_table__3__1 - location
          region_table__3__2 - location
          region_table__3__3 - location
          region_table__3__4 - location
          region_table__3__5 - location
          region_table__4__-1 - location
          region_table__4__-2 - location
          region_table__4__-3 - location
          region_table__4__-4 - location
          region_table__4__-5 - location
          region_table__4__0 - location
          region_table__4__1 - location
          region_table__4__2 - location
          region_table__4__3 - location
          region_table__4__4 - location
          region_table__4__5 - location
          region_table__5__-1 - location
          region_table__5__-2 - location
          region_table__5__-3 - location
          region_table__5__-4 - location
          region_table__5__-5 - location
          region_table__5__0 - location
          region_table__5__1 - location
          region_table__5__2 - location
          region_table__5__3 - location
          region_table__5__4 - location
          region_table__5__5 - location
          box1 - block
          -1__0__0__0 - direction
          -1__0__0__1 - direction
          -1__0__0__2 - direction
          -1__0__0__3 - direction
          0__-1__0__0 - direction
          0__-1__0__1 - direction
          0__-1__0__2 - direction
          0__-1__0__3 - direction
          0__0__1__0 - direction
          0__0__1__1 - direction
          0__0__1__2 - direction
          0__0__1__3 - direction
          0__1__0__0 - direction
          0__1__0__1 - direction
          0__1__0__2 - direction
          0__1__0__3 - direction
          1__0__0__0 - direction
          1__0__0__1 - direction
          1__0__0__2 - direction
          1__0__0__3 - direction
   )

   (:init
          (handempty)
          (ontable box1 region_drawer__0__0)
   )

   (:goal
   (and
        (handempty)
        (ontable box1 region_shelf__1__0)
   ))

)
