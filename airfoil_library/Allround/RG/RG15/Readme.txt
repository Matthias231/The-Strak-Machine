- The file RG15.dat contains the original RG15 airfoil by Rolf Girsberger without any changes

- The file RG15_SE_150k.dat contains a smoothed and repaneled (more points) version of the original airfoil.
  Thus the results in XFoil are a bit better.

- The other airfoils are my first attempt (only a small amount of time was spent) to create a set of airfoils, 
  adjusted to different ReSqrt(Cl)-numbers to form a strak.
- The airfoils have still some weaknesses, like not matching zero lift angle etc. (to be improved in the future)

- The .xfl-File can be opened with XFRL5 to get an overview about the airfoils and their polars
- The "angular" / not rounded polars are the "target"-polars, that represent the objectives for the optimizer
