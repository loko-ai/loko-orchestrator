trigger_doc = '''### Description
The TRIGGER component is used to start streams.

### Output
The parameter Type can be set as a **String** or an **Object**. The parameter Value, on the other hand, defines the actual output of the component.'''

counter_doc = '''### Description 
The COUNTER component allows you to count the number of input received from the previous component. It can be used to count the rows of your CSV file or the number of outputs returned by a given function. In order to use it you do not need to specify any configuration.

Input
In this case there is no fixed input format.

Output 
The output will be a number representing the number of counted elements.
'''

array_doc = '''### Description
The ARRAY component is used as an iterator. The array to iterate over can be defined with the parameter value or depend on the input received.

### Input
In case an input is given, it will correspond to the data to iterate on.

### Output
The number of outputs depends on the length of what is passed in input or defined in the parameter value. The output will consist of iterating element by element.'''

function_doc = '''### Description
The FUNCTION component is used to apply Python code to the input component's. The input can be retrieved using the variable *data*.

To be able to use data from components of type FUNCTION that are not linked together, the object is set repository.

```python
repository.set('value', 5) - this sets the variable value to 5.
repository.get('value') - in this way the variable is called value and the value 5 is returned.
```

### Input
The input is used by the component using the variable **data**.

### Output
The output coincides with the return of the code defined when the component was created.'''

filter_doc = '''### Description
The FILTER component is used to filter the input data. To configure this component, you need to define Python code that returns a boolean (true / false) that depends on the input received. The input can be retrieved using the variable **data**.

### Input
The input is used by the component using the variable **data**.

### Output
There are two outputs: **output** and **discarded**. Through the first output are returned the inputs that verify the condition defined inside the component, in the second those that do not verify it.'''

switch_doc = '''### Description
The SWITCH component, unlike Filter, allows you to apply more than one condition to the input data.

### Input
In this case there is no fixed input format.

### Output
Outputs are defined using the parameter **Outputs**. In this parameter it is possible to define the condition that the input must respect to be returned in the corresponding output. The input can be retrieved using the variable **data**.'''

grouper_doc = '''### Description
The GROUPER component is used to group the elements received in input. The items will be returned in batches with a maximum size equal to **Group size**.

### Input
In this case there is no fixed input format.

### Output
In output lists of elements received in input with a maximum length equal to **Group size**.'''

head_doc = '''### Description
The HEAD component is used to filter the first **Number of elements** received in input. This is a very useful component for testing the functionality of a stream.

### Input
In this case there is no fixed input format.

### Output
The first will be returned **Number of elements** received in input in output.'''

debug_doc = '''### Description
The DEBUG component is used only to view the output of other components.

### Input
In this case there is no fixed input format.'''

selector_doc = '''### Description
The SELECTOR component is used to select the value of one or more object keys. The required key/s are defined using the parameter **Keys**.

In order to add other keys you need to click on the **"Add field"** buttons.
 
If the field **Ignore Error** is toggled, missing key values are ignored.

It's also possible to select nested key, just by writing them in a *key* field, and seperating them using a full stop. Let's consider the object in the example below: if you want to have access to the content of the "key3" object, you need to use the following notation "key1.key2.key3".


```json
 {"key1":{"key2":{"key3":["val1", "val2", "val3"]}}} 
```



### Input

The input consists of a dictionary.



### Output

The output is the value of the required key of the dictionary received as input, if only one key is selected; otherwise it's an object which contains the keys specified and their value.
'''

sampler_doc = '''### Description
The SAMPLER component is used to sample the elements received in input. The parameter **Sample size** represents the number of items to receive as output.

### Input
In this case there is no fixed input format.

### Output
Are returned **Sample size** items chosen at random.'''

merge_doc = '''### Description
The MERGE component is used to merge the results of multiple components.

### Input
The number of inputs is defined using the parameter *Inputs*.

### Output
In output are returned dictionaries that have as keys the Inputs defined at the creation of the component and as values the elements received in input from the connected components.'''
