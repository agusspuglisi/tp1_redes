Ejecutar server con dirección de almacenamiento 'tests':
python3 start-server.py --host 127.0.0.1 --port 8080 --storage tests

Subir un archivo desde la carpeta raíz, a la carpeta 'tests':
python3 upload.py --host 127.0.0.1 --port 8080 --src testfile.txt --name testfile.txt