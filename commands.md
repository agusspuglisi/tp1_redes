Ejecutar server con dirección de almacenamiento 'tests' con protocolo stop&wait:
python3 start-server.py --host 127.0.0.1 --port 8080 --storage tests -r saw

Subir un archivo desde la carpeta raíz, a la carpeta 'tests' con protocolo stop&wait:
python3 upload.py --host 127.0.0.1 --port 8080 --src testfile.txt --name testfile.txt -r saw

Descargar archivo testfile en la carpeta 'downloads' con protocolo stop&wait:
python3 download.py --host 127.0.0.1 --port 8080 --name testfile.txt --dst downloads -r saw