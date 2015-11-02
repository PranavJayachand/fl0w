# fl0w

Client 1:
<pre>
.
</pre>

Client 2:
<pre>
.
└── test.py (MD5: 7984fc60703f0e3801005e042bb13c86 | Timestamp: 1445794264)
</pre>

Server:
<pre>
.
└── test.py (MD5: 354dc351e940ef48b689d4d925532053 | Timestamp: 1445794100)
</pre>



> Time = 0

Client1: **Connect**  
Client1: `{"auth" : {"user" : "test", "pw" : "123"}}`  
Server > Client1: `{"auth" : 1}`  
Client1: `{"sync" : []}`  
Server > Client1: `{"sync" : ["test.py" : {"mtime" : 1445794100}]}`  
Server > Client1: **test.py**

> Time = 1

Client2: **Connect**  
Client2: `{"auth" : {"user" : "test1", "pw" : "1233"}}`  
Server > Client2: `{"auth" : 0}`  
Client2: **Disconnects**

> Time = 2

Client2: **Connect**  
Client2: `{"auth" : {"user" : "test", "pw" : "123"}}`  
Server > Client2: `{"auth" : 1}`  
Client2: `{"sync" : ["test.py" : {"mtime" : 1445794264, "md5" : "7984fc60703f0e3801005e042bb13c86"}]}`
Server > Client2: `{"sync" : ["test.py"]}`  
Client2: **test.py**  
Server > Client1: `{"sync" : ["test.py" : {"mtime" : 1445794264}]}`  
Server > Client1: **test.py**