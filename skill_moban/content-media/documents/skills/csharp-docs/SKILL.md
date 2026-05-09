# C# Documentation Best Practices

* Public members should be documented with XML comments.
* It is encouraged to document internal members as well, especially if they are complex or not self-explanatory.

## Guidance for all APIs

Use  to provide a brief, one sentence, description of what the type or member does. Start the summary with a present-tense, third-person verb. Use  for additional information, which can include implementation details, usage notes, or any other relevant context. Use  for language-specific keywords like `null`, `true`, `false`, `int`, `bool`, etc. Use  for inline code snippets. Use  for usage examples on how to use the member. Use `` for code blocks. ``` `` tags should be placed within an  ``` tag. Add the language of the code example using the `language` attribute, for example, ``. Use  to reference other types or members inline (in a sentence). Use  for standalone (not in a sentence) references to other types or members in the "See also" section of the online docs. 
* Use  to inherit documentation from base classes or interfaces.  
  * Unless there is major behavior change, in which case you should document the differences.

## Methods

* Use  to describe method parameters.  
  * The description should be a noun phrase that doesn't specify the data type.
  * Begin with an introductory article.
  * If the parameter is a flag enum, start the description with "A bitwise combination of the enumeration values that specifies...".
  * If the parameter is a non-flag enum, start the description with "One of the enumeration values that specifies...".
  * If the parameter is a Boolean, the wording should be of the form " to ...; otherwise, .".
  * If the parameter is an "out" parameter, the wording should be of the form "When this method returns, contains .... This parameter is treated as uninitialized.".
Use  to reference parameter names in documentation. Use  to describe type parameters in generic types or methods. Use  to reference type parameters in documentation. Use  to describe what the method returns. 
  * The description should be a noun phrase that doesn't specify the data type.
  * Begin with an introductory article.
  * If the return type is Boolean, the wording should be of the form " if ...; otherwise, .".

## Constructors

  * The summary wording should be "Initializes a new instance of the class \[or struct\].".

## Properties

The  should start with: 
  * "Gets or sets..." for a read-write property.
  * "Gets..." for a read-only property.
  * "Gets \[or sets\] a value that indicates whether..." for properties that return a Boolean value.
Use  to describe the value of the property. 
  * The description should be a noun phrase that doesn't specify the data type.
  * If the property has a default value, add it in a separate sentence, for example, "The default is ".
  * If the value type is Boolean, the wording should be of the form " if ...; otherwise, . The default is ...".

## Exceptions

Use  to document exceptions thrown by constructors, properties, indexers, methods, operators, and events. 
* Document all exceptions thrown directly by the member.
* For exceptions thrown by nested members, document only the exceptions users are most likely to encounter.
* The description of the exception describes the condition under which it's thrown.  
  * Omit "Thrown if ..." or "If ..." at the beginning of the sentence. Just state the condition directly, for example "An error occurred when accessing a Message Queuing API."
