- The file RG15.dat contains the original RG15 airfoil by Rolf Girsberger without any changes

- The file RG15_SE_150k.dat contains a smoothed (SE = Smoothed Edition) and repaneled (more points) version of the original airfoil.
  Thus the results in XFoil are a bit better.

- The other airfoils were created with the Strak machine to form a set of airfoils adapted to different ReSqrt(CL) numbers.
- The suffix like "_150k" stands for the ReSqrt(CL) where the airfoil should perform best.

- The .xfl-File can be opened with XFRL5 to get an overview about the airfoils and their polars
- The "angular" / not rounded polars are the "target"-polars, that represent the objectives for the optimizer
