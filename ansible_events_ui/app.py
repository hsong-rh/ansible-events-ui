from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import asyncio
from .schemas import ProducerMessage
from .schemas import ProducerResponse
from .schemas import RuleSetBook, Inventory, Activation, ActivationLog, Extravars
from .schemas import Project
from .models import (
    rulesets,
    inventories,
    extravars,
    activations,
    activation_logs,
    projects,
)
from .manager import activate_rulesets
from .project import clone_project
from .database import database
import json


app = FastAPI()

app.mount("/eda", StaticFiles(directory="ui/dist", html=True), name="eda")

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:9000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskManager:
    def __init__(self):

        self.tasks = []


taskmanager = TaskManager()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


connnectionmanager = ConnectionManager()


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/")
async def root():
    return {"message": "Hello World"}


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/demo")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connnectionmanager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        connnectionmanager.disconnect(websocket)


@app.get("/ping")
def ping():
    return {"ping": "pong!"}


@app.post("/rulesetbook/")
async def create_rulesetbook(rsb: RuleSetBook):
    query = rulesets.insert().values(name=rsb.name, rules=rsb.rules)
    last_record_id = await database.execute(query)
    return {**rsb.dict(), "id": last_record_id}


@app.post("/inventory/")
async def create_inventory(i: Inventory):
    query = inventories.insert().values(name=i.name, inventory=i.inventory)
    last_record_id = await database.execute(query)
    return {**i.dict(), "id": last_record_id}


@app.post("/extravars/")
async def create_extravars(e: Extravars):
    query = extravars.insert().values(name=e.name, extravars=e.extravars)
    last_record_id = await database.execute(query)
    return {**e.dict(), "id": last_record_id}


@app.post("/activation/")
async def create_activation(a: Activation):
    query = rulesets.select().where(rulesets.c.id == a.rulesetbook_id)
    r = await database.fetch_one(query)
    query = inventories.select().where(inventories.c.id == a.inventory_id)
    i = await database.fetch_one(query)
    query = extravars.select().where(extravars.c.id == a.extravars_id)
    e = await database.fetch_one(query)
    cmd, proc = await activate_rulesets(
        "quay.io/bthomass/ansible-events:latest", r.rules, i.inventory, e.extravars
    )

    query = activations.insert().values(
        name=a.name,
        rulesetbook_id=a.rulesetbook_id,
        inventory_id=a.inventory_id,
        extravars_id=a.extravars_id,
    )
    last_record_id = await database.execute(query)

    task1 = asyncio.create_task(
        read_output(proc, last_record_id), name=f"read_output {proc.pid}"
    )
    taskmanager.tasks.append(task1)

    return {**a.dict(), "id": last_record_id}


async def read_output(proc, activation_id):
    line_number = 0
    done = False
    while not done:
        line = await proc.stdout.readline()
        if len(line) == 0:
            break
        line = line.decode()
        print(f"{line}", end="")
        query = activation_logs.insert().values(
            line_number=line_number,
            log=line,
            activation_id=activation_id,
        )
        await database.execute(query)
        line_number += 1
        await connnectionmanager.broadcast(json.dumps(["Stdout", dict(stdout=line)]))


@app.get("/activation_logs/", response_model=List[ActivationLog])
async def read_activation_logs(activation_id: int):
    q = activation_logs.select().where(activation_logs.c.activation_id == activation_id)
    return await database.fetch_all(q)


@app.get("/tasks/")
async def read_tasks():
    tasks = [
        dict(name=task.get_name(), done=task.done(), cancelled=task.cancelled())
        for task in taskmanager.tasks
    ]
    return tasks


@app.post("/project/")
async def create_project(p: Project):
    found_hash = await clone_project(p.url, p.git_hash)
    p.git_hash = found_hash
    query = projects.insert().values(url=p.url, git_hash=p.git_hash)
    last_record_id = await database.execute(query)
    return {**p.dict(), "id": last_record_id}


@app.get("/projects/")
async def read_projects():
    query = projects.select()
    return await database.fetch_all(query)


@app.get("/inventories/")
async def read_inventories():
    query = inventories.select()
    return await database.fetch_all(query)


@app.get("/rulesetbooks/")
async def read_rulesetbooks():
    query = rulesets.select()
    return await database.fetch_all(query)


@app.get("/extravars/")
async def read_extravars():
    query = extravars.select()
    return await database.fetch_all(query)


@app.get("/activations/")
async def read_activations():
    query = activations.select()
    return await database.fetch_all(query)
