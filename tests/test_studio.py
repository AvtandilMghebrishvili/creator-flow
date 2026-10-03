import io
import json
import time
import uuid
from urllib.parse import urlsplit, parse_qs
import pytest
from podcut.studio import Studio, in_folder
from podcut import subscriptions as S


def project(studio, folder=''):
    ident = studio.dispatch({'action': 'create_project', 'name': 'Synthetic project', 'folder': folder}, 'http://127.0.0.1:8772')['id']
    return studio.data['projects'][ident]


def test_single_connector_routes_supported_roles_and_multiple_need_assignment(tmp_path):
    studio = Studio(tmp_path)
    with pytest.raises(ValueError, match='Enable'):
        studio.route('ideas')
    studio.data['connectors']['claude']['enabled'] = True
    assert studio.route('writing')[0] == 'claude'
    with pytest.raises(ValueError, match='does not generate'):
        studio.route('images')
    studio.data['connectors']['chatgpt']['enabled'] = True
    with pytest.raises(ValueError, match='assign'):
        studio.route('writing')
    studio.data['roles']['writing'] = 'claude'
    assert studio.route('writing')[0] == 'claude'


def test_memory_revision_isolation_and_persistence(tmp_path):
    studio = Studio(tmp_path); one = project(studio); two = project(studio)
    request = {'action': 'memory', 'project': one['id'], 'revision': 0, 'memory': 'Corrected Georgian name: გიორგი'}
    studio.dispatch(request, '')
    with pytest.raises(ValueError, match='changed'):
        studio.dispatch(request, '')
    assert two['memory'] == ''
    resumed = Studio(tmp_path)
    assert resumed.data['projects'][one['id']]['memory'] == request['memory']


def test_youtube_context_attachment_is_validated_and_revision_guarded(tmp_path):
    studio = Studio(tmp_path); p = project(studio)
    context = {'schema': 'creator-flow-context-v1', 'contextKey': 'cf-12345678', 'language': 'ka',
               'source': {'kind': 'video', 'url': 'https://www.youtube.com/watch?v=abcdefghijk'}}
    request = {'action': 'page_context', 'project': p['id'], 'revision': 0, 'context': context}
    invalid = {**context, 'source': {'kind': 'video', 'url': 'https://example.com/'}}
    with pytest.raises(ValueError, match='canonical YouTube'):
        studio.dispatch({**request, 'context': invalid}, '')
    studio.dispatch(request, '')
    assert p['pageContext'] == context and not studio.data['jobs']
    with pytest.raises(ValueError, match='changed'):
        studio.dispatch(request, '')


def test_handoff_no_generation_idempotency_and_explicit_accept(tmp_path, monkeypatch):
    studio = Studio(tmp_path); p = project(studio)
    studio.data['connectors']['chatgpt'].update(enabled=True, mode='handoff')
    monkeypatch.setattr(studio.ai, 'generate', lambda *_: pytest.fail('Handoff must not call a provider'))
    request = {'action': 'ai_job', 'project': p['id'], 'revision': 0, 'role': 'writing', 'brief': 'Write a title', 'requestId': str(uuid.uuid4())}
    job = studio.dispatch(request, '')
    assert job['status'] == 'handoff' and not p['accepted']
    assert studio.dispatch(request, '')['id'] == job['id']
    with pytest.raises(ValueError, match='different work'):
        studio.dispatch({**request, 'brief': 'Changed'}, '')
    studio.dispatch({'action': 'complete_handoff', 'project': p['id'], 'job': job['id'], 'result': 'Reviewed title'}, '')
    assert p['accepted'] == []
    studio.dispatch({'action': 'accept_job', 'project': p['id'], 'job': job['id']}, '')
    assert p['accepted'][0]['text'] == 'Reviewed title'
    with pytest.raises(ValueError, match='older memory'):
        studio.dispatch({'action': 'accept_job', 'project': p['id'], 'job': job['id']}, '')


def test_images_are_handoff_even_with_subscription_connector(tmp_path):
    studio = Studio(tmp_path); p = project(studio)
    studio.data['connectors']['chatgpt']['enabled'] = True
    job = studio.dispatch({'action': 'ai_job', 'project': p['id'], 'revision': 0, 'role': 'images', 'brief': 'Create a cover', 'requestId': str(uuid.uuid4())}, '')
    assert job['status'] == 'handoff'


def test_direct_job_requires_consent_and_pins_the_selected_account(tmp_path, monkeypatch):
    studio = Studio(tmp_path); p = project(studio)
    studio.data['connectors']['chatgpt'].update(enabled=True, model='chosen-model')
    request = {'action': 'ai_job', 'project': p['id'], 'revision': 0, 'role': 'ideas', 'brief': 'Suggest ideas', 'requestId': str(uuid.uuid4())}
    with pytest.raises(ValueError, match='enable ChatGPT plan usage'):
        studio.dispatch(request, '')
    assert not studio.data['jobs']
    studio.ai.data.update(active='oaiapp_first', profiles={'oaiapp_first': {'access_token': 'synthetic', 'scopes': []}})
    with pytest.raises(ValueError, match='enable ChatGPT plan usage'):
        studio.dispatch(request, '')
    studio.ai.data['profiles']['oaiapp_first']['scopes'] = [S.PLAN_SCOPE]
    monkeypatch.setattr('podcut.studio.threading.Thread.start', lambda _: None)
    job = studio.dispatch(request, '')
    assert job['account'] == 'oaiapp_first'
    studio.ai.data['active'] = 'oaiapp_second'
    studio.perform(job['id'])
    assert studio.data['jobs'][0]['status'] == 'failed'
    assert 'account changed' in studio.data['jobs'][0]['error']


def test_local_job_boundaries_and_render_confirmation(tmp_path):
    studio = Studio(tmp_path); p = project(studio, str(tmp_path))
    with pytest.raises(ValueError, match='outside'):
        in_folder(tmp_path, str(tmp_path.parent / 'secret.txt'))
    base = {'action': 'local_job', 'project': p['id'], 'revision': 0, 'requestId': str(uuid.uuid4())}
    with pytest.raises(ValueError, match='Unsupported'):
        studio.dispatch({**base, 'operation': 'shell'}, '')
    with pytest.raises(ValueError, match='confirmation'):
        studio.dispatch({**base, 'operation': 'render'}, '')
    assert not studio.data['jobs']


def test_signin_pkce_unique_state_and_host_persist(tmp_path):
    pytest.importorskip('jwt')
    client = S.ChatGPTPlan(tmp_path)
    first = parse_qs(urlsplit(client.begin('http://127.0.0.1:8772')['url']).query)
    second = parse_qs(urlsplit(client.begin('http://127.0.0.1:8772')['url']).query)
    assert first['client_id'] == ['dynamic_agent_client']
    assert first['state'] != second['state'] and first['nonce'] != second['nonce']
    assert first['ext_agent_host_id'] == second['ext_agent_host_id']
    assert S.ChatGPTPlan(tmp_path).data['host'] == client.data['host']
    assert first['code_challenge_method'] == ['S256']
    assert S.PLAN_SCOPE in first['scope'][0]
    assert 'id_token_hint' not in first
    with pytest.raises(ValueError, match='state'):
        client.finish({'state': 'wrong', 'code': 'unused'})


def test_declined_signin_replay_and_mismatched_registration(tmp_path):
    pytest.importorskip('jwt')
    client = S.ChatGPTPlan(tmp_path)
    q = parse_qs(urlsplit(client.begin('http://127.0.0.1:8772')['url']).query)
    with pytest.raises(ValueError, match='declined'):
        client.finish({'state': q['state'][0], 'error': 'access_denied'})
    with pytest.raises(ValueError, match='state'):
        client.finish({'state': q['state'][0], 'code': 'unused'})
    client.data['profiles']['oaiapp_test'] = {'subject': 'one'}
    q = parse_qs(urlsplit(client.begin('http://127.0.0.1:8772', 'oaiapp_test')['url']).query)
    with pytest.raises(ValueError, match='different account'):
        client.finish({'state': q['state'][0], 'client_id': 'oaiapp_wrong', 'code': 'unused'})


def test_real_jwt_signature_nonce_audience_and_expiry(tmp_path, monkeypatch):
    jwt = pytest.importorskip('jwt')
    rsa = pytest.importorskip('cryptography.hazmat.primitives.asymmetric.rsa')
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())); jwk['kid'] = 'test'
    def get(url, **_):
        return {'keys': [jwk]} if url.endswith('jwks.json') else {'issuer': S.AUTH, 'jwks_uri': S.AUTH + '/.well-known/jwks.json'}
    monkeypatch.setattr(S, 'http_json', get)
    claims = {'iss': S.AUTH, 'aud': 'oaiapp_test', 'sub': 'subject', 'nonce': 'nonce', 'exp': time.time()+60}
    token = jwt.encode(claims, key, algorithm='RS256', headers={'kid': 'test'})
    client = S.ChatGPTPlan(tmp_path)
    assert client.validate_identity(token, 'oaiapp_test', 'nonce')['sub'] == 'subject'
    with pytest.raises(ValueError, match='nonce'):
        client.validate_identity(token, 'oaiapp_test', 'wrong')
    with pytest.raises(jwt.InvalidAudienceError):
        client.validate_identity(token, 'oaiapp_wrong', 'nonce')
    expired = jwt.encode({**claims, 'exp': time.time()-1}, key, algorithm='RS256', headers={'kid': 'test'})
    with pytest.raises(jwt.ExpiredSignatureError):
        client.validate_identity(expired, 'oaiapp_test', 'nonce')


def sse(*events):
    return io.BytesIO(b''.join(b'data: '+json.dumps(e).encode()+b'\n\n' for e in events))


def test_stream_requires_completed_and_never_accepts_failed_partial():
    delta = {'type': 'response.output_text.delta', 'delta': 'Draft'}
    assert S.consume_stream(sse(delta, {'type': 'response.completed'})) == 'Draft'
    with pytest.raises(ValueError, match='without response.completed'):
        S.consume_stream(sse(delta))
    for kind in ['response.failed', 'response.incomplete', 'error']:
        with pytest.raises(ValueError, match='could not complete'):
            S.consume_stream(sse(delta, {'type': kind}))


def test_refresh_rotates_atomically_and_public_state_never_has_tokens(tmp_path, monkeypatch):
    client = S.ChatGPTPlan(tmp_path)
    client.data.update(active='oaiapp_test', profiles={'oaiapp_test': {'subject': 's', 'access_token': 'old', 'refresh_token': 'refresh-old', 'expires': 0, 'scopes': [S.PLAN_SCOPE]}})
    seen = []
    def response(url, form=None, **_):
        seen.append(form)
        return {'access_token': 'new', 'refresh_token': 'refresh-new', 'expires_in': 3600, 'scope': S.PLAN_SCOPE}
    monkeypatch.setattr(S, 'http_json', response)
    assert client.token() == 'new' and len(seen) == 1
    assert client.token() == 'new' and len(seen) == 1
    assert seen[0]['client_id'] == 'oaiapp_test' and 'scope' not in seen[0]
    assert client.data['profiles']['oaiapp_test']['refresh_token'] == 'refresh-new'
    assert 'access_token' not in json.dumps(client.public())
    restored = S.ChatGPTPlan(tmp_path)
    assert restored.data['profiles']['oaiapp_test']['access_token'] == 'new'


def test_subscription_request_has_no_api_key_or_unsupported_fields(tmp_path, monkeypatch):
    client = S.ChatGPTPlan(tmp_path)
    monkeypatch.setattr(client, 'models', lambda *_: [{'id': 'account-selected-model'}])
    monkeypatch.setattr(client, 'token', lambda *_: 'synthetic-plan-token')
    requests = []
    class Response(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *_): self.close()
    def opened(request, **_):
        requests.append(request)
        return Response(sse({'type': 'response.output_text.delta', 'delta': 'Done'}, {'type': 'response.completed'}).read())
    monkeypatch.setattr(S, 'urlopen', opened)
    assert client.generate('brief', 'account-selected-model') == 'Done'
    body = json.loads(requests[0].data)
    assert body['stream'] is True and body['store'] is False
    assert 'max_output_tokens' not in body and 'tools' not in body
    assert requests[0].full_url == S.RESOURCE + '/responses'
    assert requests[0].headers['Authorization'] == 'Bearer synthetic-plan-token'


def test_cli_rejects_api_override_without_running(tmp_path, monkeypatch):
    from podcut import subscription_cli as cli
    monkeypatch.setattr(cli, 'executable', lambda _: ['vendor-cli'])
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'synthetic-only')
    monkeypatch.setattr(cli, 'run_process', lambda *_a, **_k: pytest.fail('Should not run'))
    with pytest.raises(ValueError, match='overrides'):
        cli.generate('claude', 'brief', '', tmp_path)
