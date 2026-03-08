import urllib.request, re, sys
for path in ['http://localhost:8000/','http://localhost:8000/catalog']:
    try:
        html = urllib.request.urlopen(path, timeout=5).read().decode('utf-8')
        print('\n==', path, '==')
        m = re.search(r'<meta[^>]+name=["\']csrf-token["\'][^>]*>', html, re.I)
        print('meta csrf-token:', bool(m), m.group(0)[:200] if m else '')
        found = re.findall(r'class=["\']btn add-cart|class=["\']add-cart', html)
        print('add-cart buttons found:', len(found))
        s = re.search(r'<button[^>]+class=["\'][^"\']*add-cart[^"\']*["\'][^>]*>', html)
        if s:
            print('button snippet:', s.group(0))
        if '/add_to_cart/' in html:
            sn = html.find('/add_to_cart/')
            print('add_to_cart snippet:', html[sn:sn+80])
    except Exception as e:
        print('Error fetching', path, e, file=sys.stderr)
