#!/usr/bin/env node
const { spawnSync, spawn } = require('child_process');
const { existsSync } = require('fs');
const path = require('path');

function runSync(cmd, args, opts = {}){
  const res = spawnSync(cmd, args, { stdio: 'inherit', shell: false, ...opts });
  if (res.error) throw res.error;
  if (res.status !== 0) throw new Error(`${cmd} ${args.join(' ')} exited with ${res.status}`);
}

function findPython(){
  const candidates = ['python', 'python3', 'py'];
  for (const c of candidates){
    try{
      const r = spawnSync(c, ['--version'], { encoding: 'utf8' });
      if (!r.error && r.status === 0 && r.stdout) return c;
      if (!r.error && r.status === 0 && r.stderr) return c; // algunos Python imprimen en stderr
    }catch(e){}
  }
  return null;
}

function venvPaths(){
  const isWindows = process.platform === 'win32';
  const venvDir = path.resolve(__dirname);
  const py = isWindows ? path.join(venvDir,'.venv','Scripts','python.exe') : path.join(venvDir,'.venv','bin','python');
  const pip = isWindows ? path.join(venvDir,'.venv','Scripts','pip.exe') : path.join(venvDir,'.venv','bin','pip');
  return { py, pip };
}

function main(){
  const args = process.argv.slice(2);
  const doRun = args.includes('--run');
  console.log('autosize: starting setup (node installer)');

  const pythonCmd = findPython();
  if (!pythonCmd){
    console.error('No Python executable found in PATH. Please install Python 3 and ensure `python` is available in PATH.');
    process.exit(1);
  }
  console.log('Found Python command:', pythonCmd);

  // crear el entorno virtual si falta
  if (!existsSync(path.join(__dirname, '.venv'))){
    console.log('Creating virtual environment (.venv) ...');
    runSync(pythonCmd, ['-m','venv','.venv']);
  } else {
    console.log('.venv already exists, skipping venv creation');
  }

  const { py: venvPython, pip: venvPip } = venvPaths();
  const pipExe = existsSync(venvPip) ? venvPip : null;
  const pythonExe = existsSync(venvPython) ? venvPython : pythonCmd;

  if (!pipExe){
    console.log('pip in venv not found; attempting to use venv python to ensure pip is available');
    try{ runSync(pythonExe, ['-m','ensurepip','--upgrade']); }catch(e){ console.warn('ensurepip failed:', e.message); }
  }

  // instalar dependencias
  if (existsSync(path.join(__dirname,'requirements.txt'))){
    console.log('Installing requirements from requirements.txt ...');
    const pipToUse = pipExe || pythonExe;
    const pipArgs = pipExe ? ['install','-r','requirements.txt'] : ['-m','pip','install','-r','requirements.txt'];
    runSync(pipToUse, pipArgs);
  } else {
    console.log('requirements.txt not found, skipping pip install');
  }

  // importar volcado SQL si está presente
  const importScript = path.join(__dirname,'scripts','import_sql.py');
  if (existsSync(importScript)){
    console.log('Importing SQL dump using', importScript);
    runSync(pythonExe, [importScript]);
  } else {
    console.log('import_sql.py not found, skipping SQL import');
  }

  if (doRun){
    console.log('Starting Django development server (Ctrl+C to stop)');
    const server = spawn(pythonExe, ['manage.py','runserver'], { stdio: 'inherit' });
    server.on('exit', code => process.exit(code));
  } else {
    console.log('Setup complete. To run the server, execute:');
    console.log('  ./.venv/Scripts/python.exe manage.py runserver   (Windows)');
    console.log('  ./.venv/bin/python manage.py runserver         (Linux/macOS)');
  }
}

try{ main(); }catch(err){ console.error('autosize failed:', err && err.message ? err.message : err); process.exit(1); }
