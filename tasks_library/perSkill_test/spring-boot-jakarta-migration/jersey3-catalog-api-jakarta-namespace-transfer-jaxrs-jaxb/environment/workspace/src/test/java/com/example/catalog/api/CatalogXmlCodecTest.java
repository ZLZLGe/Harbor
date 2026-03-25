package com.example.catalog.api;

import com.example.catalog.model.CatalogPreview;
import java.io.StringWriter;
import javax.xml.bind.JAXBContext;
import javax.xml.bind.Marshaller;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

class CatalogXmlCodecTest {

    @Test
    void previewCanStillBeMarshalledToExpectedXmlShape() throws Exception {
        CatalogPreview preview = new CatalogPreview(
            "sku-300",
            "Insulated Mug",
            "C7",
            "READY",
            "sku-300-insulated-mug",
            "catalog-preview"
        );

        JAXBContext context = JAXBContext.newInstance(CatalogPreview.class);
        Marshaller marshaller = context.createMarshaller();
        StringWriter writer = new StringWriter();

        marshaller.marshal(preview, writer);

        String xml = writer.toString();
        assertTrue(xml.contains("<catalogPreview"));
        assertTrue(xml.contains("<generatedBy>catalog-preview</generatedBy>"));
    }
}
