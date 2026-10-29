"""Read-only loopback native preflight, not a provider or episode client."""
import asyncio
import json
import math


def native_get(path, *, port=8000, seconds=5, transport=None):
    if path not in ('/health','/schema'):
        raise ValueError('read-only native preflight path required')
    if type(port) is not int or not 1024<=port<=65535:
        raise ValueError('explicit unprivileged loopback port required')
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=15:
        raise ValueError('finite total deadline within15seconds required')
    async def request():
        import httpx
        async with httpx.AsyncClient(transport=transport, timeout=seconds,
                                    follow_redirects=False, trust_env=False) as client:
            async with client.stream('GET',f'http://127.0.0.1:{port}{path}',
                                     headers={'Accept':'application/json'}) as r:
                if r.status_code!=200:
                    raise RuntimeError('native preflight rejected')
                body=bytearray()
                async for chunk in r.aiter_bytes():
                    body.extend(chunk)
                    if len(body)>65536:
                        raise RuntimeError('native preflight response exceeds bound')
                value=json.loads(body)
                if not isinstance(value,dict):
                    raise ValueError('native JSON object required')
                return value
    async def bounded():
        return await asyncio.wait_for(request(),timeout=seconds)
    try:
        return asyncio.run(bounded())
    except TimeoutError:
        raise TimeoutError('native total deadline reached') from None
    except Exception:
        # Never include arbitrary HTTP body, URL errors or local environment.
        raise RuntimeError('bounded native preflight failed') from None
