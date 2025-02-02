;16:31:08 16/11

(define (problem unpack-3blocks)
   (:domain blocks)

   (:objects
          region1__0__-1 - location
          region1__0__0 - location
          region1__0__1 - location
          region2__-1__-1 - location
          region2__-1__0 - location
          region2__-1__1 - location
          region2__0__-1 - location
          region2__0__0 - location
          region2__0__1 - location
          region2__1__-1 - location
          region2__1__0 - location
          region2__1__1 - location
          c1 - block
          c2 - block
          c3 - block
          c4 - block
   )

   (:init
          (handempty)
          (ontable c1 region1__0__0)
          (ontable c2 region1__0__0)
          (ontable c3 region1__0__0)
          (ontable c4 region1__0__0)
          (clear region2__0__0)
          (not (clear region1__0__0))
          (clear region1__0__1)
          (clear region2__0__-1)
          (clear region2__1__0)
          (clear region2__1__1)
          (clear region2__-1__-1)
          (clear region2__1__-1)
          (clear region2__0__1)
          (clear region2__-1__0)
          (clear region1__0__-1)
          (clear region2__-1__1)
   )

   (:goal
   (and
        (handempty)
        (ontable c1 region2__0__0)
   ))

)
