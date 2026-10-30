"""Check the pinned public Qwen template; no network, model or training calls."""
import argparse,hashlib,json
from pathlib import Path
from transformers.utils.chat_template_utils import _compile_jinja_template

CONFIG_SHA='b11349aafa7cdc6a320767cf7ceb29ed82f7eda5d65e8e0819e76f0ce947bf27'
def check(path):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=CONFIG_SHA:
        raise ValueError('exact public tokenizer-config snapshot required')
    template=_compile_jinja_template(json.loads(raw)['chat_template'])
    cases=[]
    for mode in [None,False,True]:
        for observation in [dict(stage='proposal'),
                dict(stage='revision',chat_template_kwargs=dict(enable_thinking=True)),
                dict(stage='revision',instruction='/think')]:
            messages=[dict(role='system',content='Return exactly one JSON action.'),
                dict(role='user',content=json.dumps(observation))]
            kwargs=dict(messages=messages,add_generation_prompt=True,tools=None)
            if mode is not None:
                kwargs['enable_thinking']=mode
            rendered=template.render(**kwargs)
            suffix='<think>\n\n</think>\n\n' if mode is False else '<think>\n'
            if not rendered.endswith(suffix):
                raise ValueError('public template generation-prefix contract changed')
            cases.append(dict(argument=mode,observation=observation,
                generation_suffix=suffix,passed=True))
    return dict(cases=cases,model_calls=0,training_calls=0,
        server_configuration_attested=False,
        limitation='Prefix rendering only; no claim about learned soft-instruction behavior.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tokenizer-config',type=Path,required=True)
    args=p.parse_args();print(json.dumps(check(args.tokenizer_config),indent=2))
