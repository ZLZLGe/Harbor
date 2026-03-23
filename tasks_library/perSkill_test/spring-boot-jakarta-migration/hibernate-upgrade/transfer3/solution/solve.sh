#!/bin/bash

set -euo pipefail

cd /workspace

cat > src/main/java/com/example/vendor/model/VendorProfile.java <<'EOF'
package com.example.vendor.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "vendor_profiles")
public class VendorProfile {
    @Id
    private Long id;

    @Column(name = "vendor_code", nullable = false, unique = true)
    private String vendorCode;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", nullable = false)
    private String metadataJson;
}
EOF

cat > /root/transfer3_metadata_mapping_report.md <<'EOF'
# Vendor Metadata Mapping Migration
- service: vendor-onboarding
- removed_annotations: @TypeDef, @Type
- replacement: @JdbcTypeCode(SqlTypes.JSON)
- touched_file: src/main/java/com/example/vendor/model/VendorProfile.java
EOF
