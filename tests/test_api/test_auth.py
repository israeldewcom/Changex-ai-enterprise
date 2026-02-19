def test_register(client, db):
    response = client.post('/api/v1/auth/register', json={
        'email': 'test@example.com',
        'password': 'Test1234',
        'full_name': 'Test User',
        'accept_terms': True
    })
    assert response.status_code == 201
    assert response.json['user'] is not None

def test_login(client, admin_user):
    response = client.post('/api/v1/auth/login', json={
        'email': 'admin@test.com',
        'password': 'Admin123!'
    })
    assert response.status_code == 200
    assert 'access_token' in response.json
