package com.example.catalog.model;

import java.util.ArrayList;
import java.util.List;
import javax.xml.bind.annotation.XmlAccessType;
import javax.xml.bind.annotation.XmlAccessorType;
import javax.xml.bind.annotation.XmlElement;
import javax.xml.bind.annotation.XmlElementWrapper;
import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement(name = "catalogSnapshot")
@XmlAccessorType(XmlAccessType.FIELD)
public class CatalogSnapshot {

    private String catalogName;
    private String maintainer;
    private int itemCount;

    @XmlElementWrapper(name = "items")
    @XmlElement(name = "item")
    private List<CatalogItem> items = new ArrayList<>();

    public CatalogSnapshot() {
    }

    public CatalogSnapshot(String catalogName, String maintainer, List<CatalogItem> items) {
        this.catalogName = catalogName;
        this.maintainer = maintainer;
        this.items = new ArrayList<>(items);
        this.itemCount = this.items.size();
    }

    public String getCatalogName() {
        return catalogName;
    }

    public void setCatalogName(String catalogName) {
        this.catalogName = catalogName;
    }

    public String getMaintainer() {
        return maintainer;
    }

    public void setMaintainer(String maintainer) {
        this.maintainer = maintainer;
    }

    public int getItemCount() {
        return itemCount;
    }

    public void setItemCount(int itemCount) {
        this.itemCount = itemCount;
    }

    public List<CatalogItem> getItems() {
        return items;
    }

    public void setItems(List<CatalogItem> items) {
        this.items = items;
        this.itemCount = items == null ? 0 : items.size();
    }
}
