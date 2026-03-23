package jakarta.validation.constraints;

public @interface Size {
    int min() default 0;
    int max() default Integer.MAX_VALUE;
}
