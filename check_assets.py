import urllib.request

urls = [
    '/',
    '/styles.css',
    '/js/app.js',
    '/js/api.js',
    '/js/state.js',
    '/js/dashboard.js',
    '/js/quantum_engine.js',
    '/charts/chart_fidelity.png',
    '/charts/chart_detection.png',
    '/charts/chart_boxplot.png',
    '/charts/chart_chsh.png',
    '/charts/chart_trials.png'
]

all_ok = True
for u in urls:
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:8000{u}')
        print(f'{u:<30} -> {r.status} OK ({r.headers.get("Content-Type")})')
    except Exception as e:
        print(f'{u:<30} -> ERROR: {e}')
        all_ok = False

if all_ok:
    print('\n[+] All static assets, styles, scripts, and charts served properly!')
