poetry run python setup.py build_ext --inplace


```
export PYTHONPATH=$(pwd)
python scripts/diff.py tests/data/samples/exemple_variance/la_vieille_fille_v1.xml  tests/data/samples/exemple_variance/la_vieille_fille_v2.xml --lg_pivot 7 --ratio 15 --seuil 50 --case-sensitive --diacri-sensitive --output-xml test.xml
```
