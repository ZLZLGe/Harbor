#!/bin/bash
set -euo pipefail

cat > /root/resolved_placeholders.tsv <<'EOF'
note_id	section	resolved_title	resolved_authors	year	venue	canonical_identifier
RV-01	backbone-history	Deep Residual Learning for Image Recognition	Kaiming He; Xiangyu Zhang; Shaoqing Ren; Jian Sun	2016	CVPR	10.1109/CVPR.2016.90
RV-02	feature-reuse	Densely Connected Convolutional Networks	Gao Huang; Zhuang Liu; Laurens van der Maaten; Kilian Q. Weinberger	2017	CVPR	10.1109/CVPR.2017.243
RV-03	instance-segmentation	Mask R-CNN	Kaiming He; Georgia Gkioxari; Piotr Dollar; Ross Girshick	2017	ICCV	10.1109/ICCV.2017.322
RV-04	dense-detection	Focal Loss for Dense Object Detection	Tsung-Yi Lin; Priya Goyal; Ross Girshick; Kaiming He; Piotr Dollar	2017	ICCV	10.1109/ICCV.2017.324
EOF
