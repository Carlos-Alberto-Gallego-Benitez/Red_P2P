import hashlib
import time
import json
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO, emit
import requests

# Clase Block que representa un bloque en la blockchain
class Block:
    def __init__(self, index, timestamp, messages, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.messages = messages
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

# Blockchain principal
class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_messages = []
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(0, time.time(), [], "0")
        self.chain.append(genesis_block)

    def add_block(self, block):
        self.chain.append(block)

    def create_new_block(self):
        block = Block(len(self.chain), time.time(), self.current_messages, self.chain[-1].hash)
        self.current_messages = []  # Limpiar mensajes después de crear el bloque
        self.add_block(block)
        return block

    def new_message(self, sender, content):
        self.current_messages.append({
            'sender': sender,
            'message': content
        })
        return self.get_last_block()['index'] + 1

    def get_last_block(self):
        return self.chain[-1]

# Configuración de la aplicación Flask con Socket.IO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

blockchain = Blockchain()

@app.route('/', methods=['GET'])
def index():
    imagen = request.GET['imagen']
    return render_template("index.html")

# Rutas HTTP
@app.route('/send_message', methods=['POST'])
def send_message():
    values = request.get_json()

    required = ['sender', 'message']
    if not all(k in values for k in required):
        return 'Faltan parámetros', 400

    index = blockchain.new_message(values['sender'], values['message'])
    response = {'message': f'Mensaje será añadido al bloque {index}'}
    return jsonify(response), 201

@app.route('/mine', methods=['GET'])
def mine():
    new_block = blockchain.create_new_block()
    # Emitir el nuevo bloque a todos los nodos
    socketio.emit('new_block', new_block.__dict__)
    response = {
        'message': 'Nuevo bloque minado',
        'index': new_block.index,
        'messages': new_block.messages,
        'hash': new_block.hash
    }
    return jsonify(response), 200

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': [block.__dict__ for block in blockchain.chain],
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

# Eventos Socket.IO
@socketio.on('connect')
def handle_connect():
    print('Cliente conectado')

@socketio.on('disconnect')
def handle_disconnect():
    print('Cliente desconectado')

@socketio.on('request_chain')
def send_chain():
    """Enviar la cadena completa cuando un nodo la solicite"""
    chain_data = [block.__dict__ for block in blockchain.chain]
    emit('update_chain', chain_data)

@socketio.on('new_block')
def receive_new_block(data):
    """Recibir un nuevo bloque desde otro nodo"""
    new_block = Block(
        index=data['index'],
        timestamp=data['timestamp'],
        messages=data['messages'],
        previous_hash=data['previous_hash']
    )
    if new_block.hash == new_block.calculate_hash() and new_block.previous_hash == blockchain.get_last_block().hash:
        blockchain.add_block(new_block)
        print(f"Nuevo bloque añadido: {new_block.index}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
