# mobile-participation
The infrastructure for a mobile participation game where players guess songs and answer questions on their mobile devices. The answer is sent using rabbitmq to a server, so the admin can assign points to the teams without the teams seeing each others answers.



# Usage

`python start.py <number of players>`

Several different websites will be hosted under different ports. See here:

- `server.py` ([localhost:7999](http://localhost:7999)) for receiving the mobile hosts answers and assigning points
- `monitor.py` ([localhost:8000](http://localhost:8000)) for displaying the current game state and playing the songs
- `host.py` ([localhost:8001](http://localhost:8001)-80XX) for hosting websites for the mobile hosts to answer the questions. Each Team recieves a different website/port

