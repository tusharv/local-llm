import base64
from fastapi.testclient import TestClient
from studio.main import create_app
from studio.db import connect, add_message


def test_opaque_ids_and_archive_roundtrip(tmp_path):
    app = create_app(tmp_path)
    client = TestClient(app)
    server = client.post('/api/endpoints', json={'name':'Local','kind':'ollama','base_url':'http://127.0.0.1:11434/v1'}).json()
    chat = client.post('/api/conversations', json={'endpoint_id':server['id'],'model':'test','title':'Backup test'}).json()
    assert len(chat['public_id']) == 32
    assert client.get('/api/conversations/'+chat['public_id']).json()['id'] == chat['id']
    picture = app.state.uploads_dir / 'test.png'
    picture.write_bytes(b'\x89PNG\r\n\x1a\nexample')
    with connect(app.state.db_path) as conn:
        add_message(conn, conversation_id=chat['id'], role='user', content='Hello', image_path=str(picture))
        add_message(conn, conversation_id=chat['id'], role='assistant', content='Hi', thinking='Thought')
    backup = client.get('/api/conversation-archive/'+chat['public_id'])
    assert backup.status_code == 200
    assert 'endpoint_id' not in backup.text
    imported = client.post('/api/conversation-archive', params={'endpoint_id':server['id']}, json=backup.json())
    assert imported.status_code == 201
    copy = imported.json()['conversations'][0]
    assert copy['public_id'] != chat['public_id']
    restored = client.get('/api/conversations/'+copy['public_id']).json()
    assert [m['content'] for m in restored['messages']] == ['Hello','Hi']
    assert restored['messages'][1]['thinking'] == 'Thought'
    assert client.get(restored['messages'][0]['image_url']).content == picture.read_bytes()
    # Stable across database initialization/restart.
    assert TestClient(create_app(tmp_path)).get('/api/conversations/'+chat['public_id']).status_code == 200
    invalid = backup.json()
    invalid['conversations'][0]['messages'][0]['image'] = base64.b64encode(b'<script>bad</script>').decode()
    assert client.post('/api/conversation-archive', params={'endpoint_id':server['id']}, json=invalid).status_code == 400
    assert len(client.get('/api/conversations').json()['conversations']) == 2
