# Usage

> [!IMPORTANT]
> Everything must be ran from the *root* of this repository, **do not** cd into *src/*.

```
# compile and run lattice generating script
gfortran -O2 src/latgen.f90 -o latgen
./latgen

# [optional] benchmark different LAMMPS configurations
./benchmark.sh [-ranks N] [-gpu N] [-clean]

# run the LAMMPS script you are interested in
# EXAMPLE:
./run.sh src/in.equilibration [-np N] [-omp N] [-gpu N]

# create python virtual environment and install all the stuff required
# (depending on your python installation these commands may differ)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# run the python analyzing script you are interested in
# (usually it goes like `lc.py` to generate data, `lc_vis.py` to visualise data)
# EXAMPLE:
python src/lc.py [-i INPUT] [-o OUTPUT] [-t N] [-v N]
python src/lc_vis.py [-i INPUT] [-s]
```

> [!TIP]
> Check out source code for comments

> [!TIP]
> If the bash script is not running via `./script.sh` syntax, run `chmod +x script.sh`