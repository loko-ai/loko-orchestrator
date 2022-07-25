request_doc = '''### Description
The HTTP REQUEST component is used to make HTTP requests in the web to microservices external to the LOKO AI platform.

### Input
Input is only required for HTTP methods that have or require a body (PUT/PATCH/POST). In this case there is no predefined input format.

### Output
In this case there is no fixed output format.'''

response_doc = '''### Description
The RESPONSE component is used to set the type of response output that should be sent upon receipt of an HTTP request captured by a **Route** component.

### Input
In this case there is no fixed input format.

### Output
The component has no output.'''


route_doc = '''### Description
The ROUTE component is used to create a web server listening on a specific address and a specific HTTP method.

### Input
The component has no input.

### Output
In this case there is no fixed output format.'''

template_doc = '''### Description
The TEMPLATE component is used to send an HTML template in response to the receipt of an HTTP request captured by a Route component.

### Input
In this case there is no fixed input format.

### Output
The output will be the HTML template inserted in the component configuration.'''