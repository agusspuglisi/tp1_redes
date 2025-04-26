| Command   | Direction       | Payload          | Purpose                          |
|-----------|-----------------|------------------|----------------------------------|
| `UPLOAD`  | Client → Server | Filename (str)   | Initiate file upload             |
| `DOWNLOAD`| Client → Server | Filename (str)   | Request file download            |
| `READY`   | Server → Client | None             | Acknowledge upload readiness     |
| `FOUND`   | Server → Client | None             | Confirm file exists for download |
| `NOTFOUND`| Server → Client | None             | Reject download request          |
| `EOF`     | Both Directions | None             | End of transmission              |


Client                  Server
  | -- UPLOAD file.txt --> |
  | <------- READY ------- |
  | ---- DATA Chunk 1 ---> |
  | ---- DATA Chunk 2 ---> |
  | --------- EOF -------> |



  Client                  Server
  | -- DOWNLOAD file.txt -> |
  | <------- FOUND ------- |
  | <----- DATA Chunk 1 --- |
  | <----- DATA Chunk 2 --- |
  | <-------- EOF --------- |