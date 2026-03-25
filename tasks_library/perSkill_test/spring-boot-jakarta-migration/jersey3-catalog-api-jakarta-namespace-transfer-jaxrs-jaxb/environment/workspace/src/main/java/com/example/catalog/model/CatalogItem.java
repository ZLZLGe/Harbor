package com.example.catalog.model;

import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement(name = "catalogItem")
@XmlAccessorType(XmlAccessType.FIELD)
public class CatalogItem {

    private String sku;
    private String displayName;
    private String categoryTag;
    private String warehouseZone;

    public CatalogItem() {
    }

    public CatalogItem(String sku, String displayName, String categoryTag, String warehouseZone) {
        this.sku = sku;
        this.displayName = displayName;
        this.categoryTag = categoryTag;
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

    public String getCategoryTag() {
        return categoryTag;
    }

    public void setCategoryTag(String categoryTag) {
        this.categoryTag = categoryTag;
    }

    public String getWarehouseZone() {
        return warehouseZone;
    }

    public void setWarehouseZone(String warehouseZone) {
        this.warehouseZone = warehouseZone;
    }
}
