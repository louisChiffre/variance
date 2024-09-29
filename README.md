installation

install poetry


to generate suffix tree extension necessary for medite

```
poetry run python setup.py build_ext --inplace
```


usage


to generate difference from tei xml
```
export PYTHONPATH=$(pwd)
python scripts/diff.py tests/data/samples/exemple_variance/la_vieille_fille_v1.xml  tests/data/samples/exemple_variance/la_vieille_fille_v2.xml --lg_pivot 7 --ratio 15 --seuil 50 --case-sensitive --diacri-sensitive --output-xml test.xml
```

to generate difference from text files

```
python scripts/diff.py tests/data/samples/post_processing/1vf.txt  tests/data/samples/post_processing/2vf.txt  --lg_pivot 7 --ratio 15 --seuil 50 --case-sensitive --diacri-sensitive --output-xml vf_v1_v2.xml
```
