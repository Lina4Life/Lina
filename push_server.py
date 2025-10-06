"""
Simple push server to store subscriptions and send Web Push notifications using pywebpush.
On first run it will generate a VAPID key pair and save it to vapid_private.pem and vapid_public.pem.

Usage (development):
  python push_server.py

This server is intentionally minimal for local testing. Production usage requires HTTPS and secure storage.
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from pathlib import Path
from pywebpush import webpush, WebPushException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

APP = Flask(__name__, static_folder='static')
CORS(APP)

BASE = Path(__file__).parent
SUB_FILE = BASE / 'subscriptions.json'
VAPID_PRIV = BASE / 'vapid_private.pem'
VAPID_PUB = BASE / 'vapid_public.pem'

def load_subscriptions():
    if SUB_FILE.exists():
        try:
            return json.loads(SUB_FILE.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []

def save_subscriptions(items):
    try:
        SUB_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

def ensure_vapid():
    # generate an EC key (P-256) and expose public key in uncompressed SEC1 format (base64 urlsafe)
    if VAPID_PRIV.exists() and VAPID_PUB.exists():
        return
    # generate key
    key = ec.generate_private_key(ec.SECP256R1())
    priv = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    VAPID_PRIV.write_bytes(priv)
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    VAPID_PUB.write_bytes(pub)
    # Also write a base64url-encoded uncompressed public key for browser subscription
    try:
        numbers = key.public_key().public_numbers()
        x = numbers.x.to_bytes(32, 'big')
        y = numbers.y.to_bytes(32, 'big')
        uncompressed = b'\x04' + x + y
        import base64
        b64 = base64.urlsafe_b64encode(uncompressed).rstrip(b'=').decode('ascii')
        (BASE / 'vapid_public_key.txt').write_text(b64, encoding='utf-8')
    except Exception:
        pass

@APP.route('/vapid_public')
def vapid_public():
    ensure_vapid()
    # return the urlsafe-base64 public key if available, otherwise the PEM
    p = BASE / 'vapid_public_key.txt'
    if p.exists():
        return p.read_text(encoding='utf-8')
    return send_from_directory(str(BASE), VAPID_PUB.name)


@APP.route('/')
def index():
        # simple info page with link to register
        html = """
        <html><head><meta charset='utf-8'><title>Lina Push Server</title></head>
        <body>
        <h2>Lina Push Server</h2>
        <p>This server stores subscriptions and can send pushes to them.</p>
        <p><a href="/register" target="_blank">Open registration page (recommended)</a></p>
        <p>Endpoints: <ul><li>/vapid_public (GET) - returns VAPID public key</li><li>/subscribe (POST) - store subscription</li><li>/push (POST) - send push</li></ul></p>
        </body></html>
        """
        return html


@APP.route('/register')
def register_page():
        # Serve a top-level registration page that registers the service worker on this origin,
        # requests Notification permission, subscribes and posts subscription to /subscribe.
        html = """
        <!doctype html>
        <html>
        <head><meta charset='utf-8'><title>Register for Lina Push</title></head>
        <body style='font-family: sans-serif; padding:20px;'>
        <h2>Register for notifications</h2>
        <p>This page will request notification permission and register a service worker on <strong>this</strong> origin (localhost:5001).</p>
        <div id='status'>Starting...</div>
        <script>
        async function go(){
            const status = (s)=>{document.getElementById('status').innerText = s; console.log(s)};
            if(!('serviceWorker' in navigator)){ status('Service workers not supported'); return; }
            try{
                status('Registering service worker...');
                await navigator.serviceWorker.register('/static/sw.js');
                status('Requesting notification permission...');
                const perm = await Notification.requestPermission();
                if(perm !== 'granted'){ status('Permission not granted: ' + perm); return; }
                status('Fetching VAPID key...');
                const r = await fetch('/vapid_public');
                const pub = await r.text();
                function urlBase64ToUint8Array(base64String) {
                        const padding = '='.repeat((4 - base64String.length % 4) % 4);
                        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
                        const rawData = window.atob(base64);
                        const outputArray = new Uint8Array(rawData.length);
                        for (let i = 0; i < rawData.length; ++i) {
                                outputArray[i] = rawData.charCodeAt(i);
                        }
                        return outputArray;
                }
                status('Subscribing to push manager...');
                const reg = await navigator.serviceWorker.ready;
                const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(pub) });
                status('Sending subscription to server...');
                await fetch('/subscribe', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(sub)});
                status('Subscribed successfully — you may close this window.');
            }catch(e){
                document.getElementById('status').innerText = 'Error: ' + e;
                console.error(e);
            }
        }
        go();
        </script>
        </body>
        </html>
        """
        return html

@APP.route('/subscribe', methods=['POST'])
def subscribe():
    payload = request.get_json()
    if not payload:
        return jsonify({'error':'invalid'}), 400
    subs = load_subscriptions()
    # simple dedupe by endpoint
    endpoint = payload.get('endpoint') or payload.get('subscription', {}).get('endpoint')
    if not endpoint:
        return jsonify({'error':'no endpoint'}), 400
    # store the raw subscription object
    exists = any(s.get('endpoint') == endpoint for s in subs)
    if not exists:
        subs.append(payload)
        save_subscriptions(subs)
    return jsonify({'ok': True})

@APP.route('/list_subs')
def list_subs():
    return jsonify(load_subscriptions())

@APP.route('/push', methods=['POST'])
def push():
    data = request.get_json() or {}
    # payload should be {'endpoint': '<url>'} or {'subscription': {...}} or {'message': '...'}
    subs = load_subscriptions()
    message = data.get('message', 'You have a new message')
    # read VAPID private key bytes
    ensure_vapid()
    vapid_priv_bytes = VAPID_PRIV.read_bytes()
    # send to all subscriptions unless endpoint specified
    target = data.get('endpoint')
    sent = []
    failed = []
    for s in subs:
        try:
            if target and s.get('endpoint') != target:
                continue
            webpush(
                subscription_info=s,
                data=json.dumps({'title':'Lina App', 'body': message}),
                vapid_private_key=vapid_priv_bytes,
                vapid_claims={"sub": "mailto:youssefelgharib03@gmail.com"}
            )
            sent.append(s.get('endpoint'))
        except WebPushException as ex:
            failed.append({'endpoint': s.get('endpoint'), 'error': str(ex)})
    return jsonify({'sent': sent, 'failed': failed})

if __name__ == '__main__':
    ensure_vapid()
    APP.run(host='0.0.0.0', port=5001, debug=True)
