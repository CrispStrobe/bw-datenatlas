"""Structural geodata pipeline test on artificial shapes in a temporary directory.

These shapes are NOT BW boundaries, are NEVER published, and do not verify the
real archive's schema or the actual municipality name correspondence.
"""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('prepare',ROOT/'scripts/prepare_geometry.py')
PREP=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(PREP)

class GeometryUnitTests(unittest.TestCase):
    def test_exact_name_normalization(self):
        self.assertEqual(PREP.norm_name('Stuttgart, Landeshauptstadt'),'stuttgart')
        self.assertEqual(PREP.norm_name('Öhringen'),'ohringen')
        self.assertEqual(PREP.norm_name('Rheinfelden (Baden)'),'rheinfeldenbaden')
        self.assertNotEqual(PREP.norm_name('Heilbronn'),PREP.norm_name('Neckarwestheim'))

    @unittest.skipUnless(all(importlib.util.find_spec(m) for m in ['shapefile','shapely','pyproj']), 'optional geography dependencies not installed')
    def test_pipeline_with_temporary_synthetic_archive(self):
        import shapefile
        from pyproj import CRS
        a=json.loads((ROOT/'docs/data/atlas.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(prefix='atlas-synthetic-test-') as temp:
            p=Path(temp);archive=p/'SYNTHETIC_NOT_BKG.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for level,rows in [('krs',a['districts']),('gem',a['municipalities'])]:
                    shp,shx,dbf=io.BytesIO(),io.BytesIO(),io.BytesIO()
                    w=shapefile.Writer(shp=shp,shx=shx,dbf=dbf,shapeType=shapefile.POLYGON,encoding='utf-8')
                    w.field('AGS','C',8);w.field('GEN','C',120);w.field('BEZ','C',30);w.field('GF','N',1,0)
                    seq={}
                    for i,r in enumerate(rows):
                        if level=='krs': ags=r['id'];name=r['name'].split(' (')[0]
                        else:
                            d=r['district_code'];seq[d]=seq.get(d,0)+1
                            ags=d+str(seq[d]).zfill(3);name=r['municipality_name']
                        x=480000+(i%35)*200;y=5400000+(i//35)*200
                        # Clockwise outer ring in a projected CRS; not a real geography.
                        w.poly([[[x,y],[x,y+150],[x+150,y+150],[x+150,y],[x,y]]])
                        w.record(ags,name,'synthetic-test-only',4)
                    w.close()
                    for ext,content in [('shp',shp.getvalue()),('shx',shx.getvalue()),('dbf',dbf.getvalue()),('prj',CRS.from_epsg(25832).to_wkt().encode()),('cpg',b'UTF-8')]:
                        z.writestr('test/VG250_'+level.upper()+'.'+ext,content)
            out=p/'geometry.json'
            result=subprocess.run([sys.executable,str(ROOT/'scripts/prepare_geometry.py'),'--archive',str(archive),'--output',str(out)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            g=json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(len(g['districts']),44)
            self.assertEqual(g['municipality_match_count'],1101)
            self.assertEqual(len(g['municipalities_unmatched']),0)
            self.assertTrue((p/'geometry-data.js').is_file())
            self.assertTrue((p/'geometry-status.json').is_file())
            self.assertTrue(all(7<f['properties']['label_point'][0]<11 for f in g['municipalities']))
        # The supplied project placeholder / real build is never overwritten by this test.

if __name__=='__main__': unittest.main(verbosity=2)
