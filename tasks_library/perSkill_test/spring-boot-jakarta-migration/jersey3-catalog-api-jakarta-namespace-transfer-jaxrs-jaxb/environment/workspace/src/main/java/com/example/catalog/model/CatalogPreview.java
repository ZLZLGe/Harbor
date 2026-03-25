package com.example.catalog.model;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement(name = "catalogPreview")
@XmlAccessorType(XmlAccessType.FIELD)
public class CatalogPreview {

    private String sku;
    private String displayName;
    private String warehouseZone;
    private String status;
    private String slug;
    private String generatedBy;

    public CatalogPreview() {
    }

    public CatalogPreview(
        String sku,
        String displayName,
        String warehouseZone,
        String status,
        String slug,
        String generatedBy
    ) {
        this.sku = sku;
        this.displayName = displayName;
        this.warehouseZone = warehouseZone;
        this.status = status;
        this.slug = slug;
        this.generatedBy = generatedBy;
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

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getSlug() {
        return slug;
    }

    public void setSlug(String slug) {
        this.slug = slug;
    }

    public String getGeneratedBy() {
        return generatedBy;
    }

    public void setGeneratedBy(String generatedBy) {
        this.generatedBy = generatedBy;
    }
}
