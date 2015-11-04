# fl0w

Client 1:
<pre>
.
</pre>

Client 2:
<pre>
.
└── test.py (MD5: bbf9a688d7c2447c7c3962a3aae6562e)
</pre>

Client 3:
<pre>
.
</pre>

Server:
<pre>
.
└── test.py (MD5: 354dc351e940ef48b689d4d925532053)
</pre>



Client1: **Connect**   
Client1: `{"sync" : []}`  
Server > Client1: `{"sync" : ["test.py": {"md5" : "354dc351e940ef48b689d4d925532053"}]}`   
Client1: `{"sync" : ["test.py"]}`
Server > Client1: **test.py**


Client2: **Connect**    
Server > Client2: `{"sync" : ["test.py": {"md5" : "354dc351e940ef48b689d4d925532053"]}`  
Client2: `{"sync" : ["test.py"]}`  
Client2: **deletes test.py**  
Server > Client2: **test.py**  


Client2: **Changes test.py**  
Client2: `{"sync" : ["test.py" : {"md5" : "0cbcc3416544206f8789391dc6805f8e"}}`  
Client2: **test.py**  
Server (Broadcast): `{"sync" : ["test.py" : {"md5" : "0cbcc3416544206f8789391dc6805f8e"}}`
Server (Broadcast): **test.py**

Client2: **Deletes test.py**  
Client2: `{"sync" : ["test.py" : {"md5" : "0"}}`  
Server (Broadcast): `{"sync" : ["test.py" : {"md5" : "0"}}`

Client3: **Connect**   
Server > Client3: `{"sync" : []}`  
Client3:  `{"sync" : []}` 

Client3: **Creates test1.py**  
Client3: `{"sync" : ["test1.py" : {"md5" : "1cbcc3416544206f8789391dc6805f8e"}}`  
Client3: **test1.py**  
Server (Broadcast): `{"sync" : {"test1.py" : {"md5" : "1cbcc3416544206f8789391dc6805f8e"}}`
Server (Broadcast): **test1.py**

Client3: **Creates test2.py**  
Client3: `{"sync" : ["test2.py" : {"md5" : "2cbcc3416544206f8789391dc6805f8e"}}`  
Client3: **test2.py**  
Server (Broadcast): `{"sync" : {"test2.py" : {"md5" : "2cbcc3416544206f8789391dc6805f8e"}}`
Server (Broadcast): **test2.py**

Client3: **Creates test3.py**  
Client3: `{"sync" : ["test3.py" : {"md5" : "3cbcc3416544206f8789391dc6805f8e"}}`  
Client3: **test3.py**  
Server (Broadcast): `{"sync" : {"test3.py" : {"md5" : "3cbcc3416544206f8789391dc6805f8e"}}`
Server (Broadcast): **test3.py**

Client1: **Deletes test2.py**  
Client1: `{"sync" : ["test2.py" : {"md5" : "0"}}`  
Server (Broadcast): `{"sync" : ["test2.py" : {"md5" : "0"}}`  

Client2: **Changes test3.py**  
Client2: `{"sync" : ["test3.py" : {"md5" : "7cbcc3416544206f8789391dc6805f8e"}}`  
Client2: **test3.py**  
Server (Broadcast): `{"sync" : ["test3.py" : {"md5" : "7cbcc3416544206f8789391dc6805f8e"}}`
Server (Broadcast): **test3.py**
