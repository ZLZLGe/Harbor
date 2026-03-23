package org.springframework.web.bind.annotation;

import org.springframework.http.HttpStatus;

public @interface ResponseStatus {
    HttpStatus value();
}
