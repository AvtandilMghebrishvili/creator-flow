"""Run user-installed, unmodified vendor CLIs. Never read or forward their tokens."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def executable(provider):
    override = os.environ.get('CREATOR_FLOW_' + provider.upper() + '_CLI')
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_file():
            return None
        if path.suffix in ('.js', '.mjs', '.cjs'):
            node = shutil.which('node')
            return [node, str(path)] if node else None
        if path.suffix.lower() in ('.exe', ''):
            return [str(path)]
        return None
    path = shutil.which(provider)
    if path and Path(path).suffix.lower() not in ('.cmd', '.bat', '.ps1'):
        return [path]
    # Avoid cmd.exe interpretation: launch npm's real vendor entrypoint with node.
    if path:
        package = '@google/gemini-cli' if provider == 'gemini' else '@anthropic-ai/claude-code'
        root = Path(path).parent / 'node_modules' / package
        metadata = root / 'package.json'
        if metadata.is_file():
            bins = json.loads(metadata.read_text(encoding='utf-8')).get('bin', {})
            name = bins.get(provider) if isinstance(bins, dict) else bins
            entry = (root / name).resolve() if name else None
            if entry and entry.is_relative_to(root.resolve()) and entry.is_file():
                if entry.suffix.lower() == '.exe':
                    return [str(entry)]
                node = shutil.which('node')
                if node and entry.suffix in ('.js', '.mjs', '.cjs'):
                    return [node, str(entry)]
    return None


def run_process(command, prompt=None, cwd=None, env=None, timeout=180):
    kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    try:
        result = subprocess.run(command, input=prompt, text=True, encoding='utf-8', errors='replace',
                                capture_output=True, cwd=cwd, env=env, timeout=timeout, shell=False, **kwargs)
    except subprocess.TimeoutExpired:
        raise ValueError('Vendor CLI timed out; outcome may be uncertain. No automatic retry.') from None
    if result.returncode:
        raise ValueError('Vendor CLI could not complete the request. Open the official CLI to check sign-in, quota and version. No API fallback.')
    if len(result.stdout) > 1_000_000:
        raise ValueError('Vendor CLI output exceeded the limit.')
    return result.stdout


def generate(provider, prompt, model, root):
    command = executable(provider)
    if not command:
        raise ValueError('Install the official ' + provider + ' CLI and sign in there first.')
    env = dict(os.environ)
    forbidden = ['ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'GEMINI_API_KEY',
                 'GOOGLE_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_GENAI_USE_VERTEXAI',
                 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY']
    if any(env.get(key) for key in forbidden):
        raise ValueError('This process has API/alternate credential overrides. Start the companion in a clean terminal for subscription-only work.')
    with tempfile.TemporaryDirectory(prefix='request-', dir=root) as work:
        work = Path(work)
        if provider == 'claude':
            status = json.loads(run_process(command + ['auth', 'status', '--json'], cwd=work, env=env, timeout=20))
            if status.get('authMethod') != 'claude.ai' or not status.get('loggedIn'):
                raise ValueError('Sign in to unmodified Claude Code with your Claude account. This connector does not accept API billing.')
            args = ['--safe-mode', '--restricted', '-p', '--output-format', 'json', '--tools', '', '--disallowedTools', 'mcp__*',
                    '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--setting-sources', '',
                    '--no-session-persistence', '--disable-slash-commands']
        else:
            settings = Path.home() / '.gemini' / 'settings.json'
            data = json.loads(settings.read_text(encoding='utf-8')) if settings.is_file() else {}
            if data.get('security', {}).get('auth', {}).get('selectedType') != 'oauth-personal':
                raise ValueError('Open Gemini CLI and choose Sign in with Google first; API-key/Vertex modes are not used.')
            policy = work / 'deny-tools.toml'
            policy.write_text('[[rule]]\ntoolName = "*"\ndecision = "deny"\npriority = 999\n', encoding='utf-8')
            system = work / 'system.json'
            system.write_text(json.dumps({'adminPolicyPaths': [str(policy)], 'hooks': {'enabled': False},
                                         'mcp': {'allowed': []}, 'general': {'enableAutoUpdate': False}}), encoding='utf-8')
            env['GEMINI_CLI_SYSTEM_SETTINGS_PATH'] = str(system)
            args = ['--prompt', 'Answer the task supplied on standard input. Do not call tools.', '--output-format', 'json',
                    '--extensions', 'none', '--admin-policy', str(policy), '--approval-mode', 'plan']
        if model:
            args += ['--model', model]
        raw = json.loads(run_process(command + args, prompt, work, env))
        value = raw.get('result') if provider == 'claude' else raw.get('response')
        if raw.get('is_error') or raw.get('error') or not isinstance(value, str) or not value.strip() or len(value) > 50000:
            raise ValueError('Vendor CLI did not return a complete bounded text result.')
        return value


def login(provider, root):
    if provider not in ('claude', 'gemini'):
        raise ValueError('Unknown vendor.')
    command = executable(provider)
    if not command:
        raise ValueError('Install the official vendor CLI first.')
    if os.name != 'nt':
        raise ValueError('Open the official CLI in your terminal to sign in: claude auth login, or gemini.')
    work = Path(root) / 'vendor-sign-in'
    work.mkdir(exist_ok=True)
    args = command + (['auth', 'login'] if provider == 'claude' else [])
    # The user explicitly clicked Open sign-in terminal. Auth stays in the vendor app.
    subprocess.Popen(args, cwd=work, creationflags=subprocess.CREATE_NEW_CONSOLE, shell=False)
    return {'opened': True, 'note': 'Finish sign-in in the vendor app. Opening it does not verify access.'}
