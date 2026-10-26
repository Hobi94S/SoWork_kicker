# SoWork Kicker

Aplicação leve em Python para verificar a presença de usuários do SoWork enviando uma mensagem de confirmação e aguardando uma resposta na mesma conversa. No modo padrão, a ferramenta executa em simulação e apenas registra quem seria desconectado, sem executar a desconexão real.

## Visão geral

A ideia é repetir a abordagem do Spot Kicker para o ambiente do SoWork, preservando o padrão de:

- selecionar usuários conectados;
- enviar uma mensagem de verificação;
- validar apenas respostas do próprio usuário na mesma conversa, após a mensagem enviada;
- cancelar a desconexão quando a resposta chega antes do prazo;
- expirar a validação e registrar a desconexão prevista quando o prazo vence;
- suspender a ação e registrar falhas de leitura, sem tratar erro como ausência de resposta.

## Configuração

1. Crie um ambiente virtual e instale as dependências:

```bash
cd /home/fabio/workspace/SoWork_kicker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

2. Ajuste as variáveis em `.env`:

```env
SOWORK_VERIFICATION_MESSAGE="Por favor, responda esta mensagem para confirmar que continua conectado ao ambiente."
SOWORK_RESPONSE_TIMEOUT_SECONDS=120
SOWORK_SIMULATION=true
SOWORK_EXEMPT_USERS="admin,coordenador"
SOWORK_APP_URL=https://app.sowork.com
SOWORK_ENVIRONMENT_NAME="SoWork"
SOWORK_OUTPUT_DIR=output
SOWORK_LOG_DIR=logs
SOWORK_PROFILE_DIR=profiles/sowork-kicker
```

## Execução

### Modo simulação (padrão)

```bash
python3 -m sowork_kicker.app
```

Esse modo registra quem seria desconectado e por quê, sem encerrar a sessão real do usuário.

### Modo com desconexão real

```bash
python3 -m sowork_kicker.app --real
```

> O modo real só deve ser usado quando a conta autenticada tiver permissão explícita para encerrar a conexão do usuário e a operação administrativa equivalente existir no SoWork. Em ambientes sem essa operação, o projeto deve permanecer em simulação.

## Estrutura do projeto

- `sowork_kicker/config.py`: leitura da configuração e variáveis de ambiente.
- `sowork_kicker/client.py`: abstração do cliente SoWork e integração administrativa.
- `sowork_kicker/engine.py`: regras de verificação, prazo, resposta válida e desconexão.
- `sowork_kicker/models.py`: tipos de estado/resultados.
- `tests/test_kicker.py`: testes do comportamento core do fluxo.

## Limitações conhecidas

- O projeto usa a mesma abordagem de autenticação e sessão do SoWork Inspector, mas não inventa endpoints administrativos do SoWork.
- Se a conta autenticada não tiver um comando de desconexão equivalente, a execução real não é possível e o sistema permanece em simulação.
- A validação de resposta exige que a própria conversa e o próprio usuário sejam rastreados corretamente; mensagens antigas, mensagens do bot e mensagens de terceiros são ignoradas.

## Validação

```bash
cd /home/fabio/workspace/SoWork_kicker
python3 -m unittest discover -s tests -v
```
