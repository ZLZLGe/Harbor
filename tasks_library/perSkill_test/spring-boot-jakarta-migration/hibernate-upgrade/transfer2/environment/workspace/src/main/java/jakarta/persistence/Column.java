package jakarta.persistence;

public @interface Column {
    boolean nullable() default true;
    boolean unique() default false;
    String name() default "";
}
