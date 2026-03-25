import csv
from pathlib import Path
mapping = {'phase_picking': ('phasenet', 'classify', 'discrete-picks'), 'detection': ('cred', 'classify', 'discrete-detections'), 'denoising': ('deepdenoiser', 'annotate', 'annotation-stream'), 'depth_estimation': ('depthphasenet', 'classify', 'discrete-estimates')}
expected = []
with Path('/root/data/mission_types.csv').open(encoding='utf-8', newline='') as handle:
    for item in csv.DictReader(handle):
        decision = mapping[item['target_task']]
        expected.append({'mission_id': item['mission_id'], 'target_task': item['target_task'], 'recommended_model_family': decision[0], 'api_mode': decision[1], 'output_shape': decision[2]})
with Path('/root/transfer3_capability_matrix.csv').open(encoding='utf-8', newline='') as handle:
    actual = list(csv.DictReader(handle))
assert actual == expected
