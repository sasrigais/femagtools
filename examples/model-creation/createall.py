import femagtools
import importlib
import os
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s')

models = ['stator1-magnetIron2',
          'stator1-magnetIron3',
          'stator1-magnetIron4',
          'stator1-magnetIron5',
          'stator1-magnetIronV',
          'stator1-magnetSector',
          'stator1-spoke',
          'stator4-magnetSector',
          'statorRotor3-magnetIron',
          'statorRotor3-ipm-fml',
          'stator1-magnetSector-pm-sym-fast']

logger = logging.getLogger("fslcreator")
workdir = os.path.join(os.path.expanduser('~'), 'femag')
logger.info("Femagtools Version %s", femagtools.__version__)
for m in models:
    mod = importlib.import_module(m)
    logger.info("--> %s <--", m)
    with open(os.path.join(workdir, m+'.fsl'), 'w') as f:
        f.write('\n'.join(getattr(mod, 'create_fsl')()))