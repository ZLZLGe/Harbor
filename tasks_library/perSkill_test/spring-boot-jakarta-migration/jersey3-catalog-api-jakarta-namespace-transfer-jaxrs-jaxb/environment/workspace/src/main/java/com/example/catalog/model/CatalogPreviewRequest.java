package com.example.catalog.model;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement(name = "catalogPreviewRequest")
@XmlAccessorType(XmlAccessType.FIELD)
public class CatalogPreviewRequest {

    private String sku;
    private String displayName;
    private String warehouseZone;

    public CatalogPreviewRequest() {
    }

    public CatalogPreviewRequest(String sku, String displayName, String warehouseZone) {
        this.sku = sku;
        this.displayName = displayName;
        this.warehouseZone = warehouseZone;
    }

    public String getSku() {
        return sku;
    }

    public void setSku(String sku) {
        this.sku = sku;
    }

    public String getDisplayName() {
        return displayName;
    }

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }

    public String getWarehouseZone() {
        return warehouseZone;
    }

    public void setWarehouseZone(String warehouseZone) {
        this.warehouseZone = warehouseZone;
    }
}
