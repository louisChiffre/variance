
To build suffix_tree module
```
poetry run python setup.py build_ext --inplace
```

Example of running a comparison
```
ipython scripts/process.py tests/data/samples/exemple_variance/la_vieille_fille_v1.xml  tests/data/samples/exemple_variance/la_vieille_fille_v2.xml -- --lg_pivot 7 --ratio 15 --seuil 50 --case-sensitive --diacri-sensitive     
```
