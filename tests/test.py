import time
import docker


client = docker.client.from_env()

n = 6
ITERATIONS = 20


def create_remove():
    containers = [
        client.containers.run(image=f'test',
                              name=f'test{i}',
                              detach=True,
                              volumes={f'test{i}': {
                                  'bind': '/data', 'mode': 'rw'}
                              })
        for i in range(n)
    ]
    print('Containers created')
    time.sleep(2)
    for c in containers:
        c.remove(force=True)
    print('Containers removed')


def create_volumes():
    volumes = [
        client.volumes.create(name=f'test{i}', driver='lvmpy')
        for i in range(n)
    ]
    for v in volumes:
        print(v)


def create_containers():
    containers = [
        client.containers.run(image=f'test',
                              name=f'test{i}',
                              detach=True,
                              volumes={f'test{i}': {
                                  'bind': '/data', 'mode': 'rw'}
                              })
        for i in range(n)
    ]
    for c in containers:
        print(c)
    return containers


def remove_containers(containers):
    for c in containers:
        c.remove(force=True)
    print('Containers removed')


def test_containers_creation():
    containers = create_containers()
    time.sleep(15)
    remove_containers(containers)
