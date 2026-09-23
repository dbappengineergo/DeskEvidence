# DeskEvidence 📸
> **Sistema Modular de Coleta e Gestão de Evidências em Desktop para Windows**

O **DeskEvidence** é uma aplicação nativa e leve para Windows, desenvolvida para rodar silenciosamente em segundo plano (**System Tray / Bandeja do Sistema**). Seu objetivo é facilitar e automatizar a coleta organizada de evidências visuais (screenshots da janela ativa ou tela inteira) vinculadas a chamados, tickets de suporte, incidentes e projetos em andamento.

---

## ✨ Principais Capacidades

- **Coleta Vinculada a Chamados/Projetos**:
  - Inicie um chamado informando Identificador/Número (ex: `INC12345`), Nome/Título e descrição inicial opcional.
  - Enquanto o chamado estiver ativo, todas as evidências capturadas são salvas e catalogadas na pasta dedicada do chamado.
- **Captura Inteligente da Janela Ativa (Padrão)**:
  - Focado na produtividade: captura exclusivamente o aplicativo em uso no momento (com compensação de DPI e bordas reais via Windows API), sem capturar telas secundárias ou informações desnecessárias.
  - Opção de alternar facilmente para captura de tela inteira (multimonitor) nas configurações.
- **Editor de Marcações Interativo estilo Lightshot (Lightbox)**:
  - Após acionar a captura (`Ctrl + Shift + E`), uma tela de edição completa inspirada no Lightshot é aberta antes de salvar.
  - **Ferramentas de Anotação**: Retângulo (R), Seta indicativa (A), Caneta livre (P), Linha reta (L), Marca-texto translúcido (H), Inserção de Texto (T), Passo Numérico sequencial 1, 2, 3... (N) e Recorte/Crop (C).
  - **Paleta de Cores e Espessuras**: Cores rápidas e espessuras de traço com renderização em alta resolução.
  - **Histórico Completo**: Desfazer (`Ctrl + Z`), Refazer (`Ctrl + Y`) e Limpar.
  - **Salvamento Controlado**: A evidência **somente é gravada no chamado se o usuário confirmar** no botão "Salvar Evidência" (`Enter` ou `Ctrl + S`). Se descartar (`Esc`), nada é gravado.
  - **Cópia Instantânea**: Botão "Copiar" (`Ctrl + C`) para transferir a imagem anotada diretamente para a Área de Transferência do Windows.
- **Relatório Consolidado em HTML**:
  - Ao finalizar um chamado, o DeskEvidence gera automaticamente um documento `relatorio_evidencias.html` estilizado e pronto para impressão/exportação em PDF, com cronologia, carimbo de data/hora, janelas capturadas e descrições.
- **Atalhos Globais Não Conflitantes e Seguros**:
  - Utiliza a API oficial `RegisterHotKey` do Windows, garantindo segurança corporativa (sem disparar falsos positivos de antivírus/EDR como ferramentas que usam hooks de teclado `SetWindowsHookEx`).
  - Atalho padrão de captura: `Ctrl + Shift + E` (não conflita com o `Win + Shift + S` ou `PrintScreen` nativo do Windows).
  - Atalho de chamados: `Ctrl + Shift + P` (cria novo se nenhum ativo, ou abre gerenciamento/finalização do ativo).
  - Totalmente reconfigurável na tela de configurações.
- **Presença em Segundo Plano (System Tray)**:
  - Ícone dinâmico na bandeja do sistema: cor azul quando inativo, ponto verde brilhante quando há chamado ativo.
  - Tooltip informativo e menu de contexto com acesso rápido a todas as funções.

---

## 📁 Estrutura do Projeto

```
DeskEvidence/
├── .venv/                         # Ambiente virtual isolado (não copiar para outros PCs)
├── .gitignore                     # Arquivos ignorados pelo Git
├── requirements.txt               # Dependências do projeto
├── build_exe.bat                  # Compila o projeto em um executável autônomo (.exe)
├── instalar_e_executar.bat        # Auto-instalador para executar o código em outro PC
├── run.bat                        # Inicializador rápido para desenvolvimento local
├── run.ps1                        # Script de inicialização em PowerShell
├── README.md                      # Documentação completa
├── dist/                          # Pasta contendo o executável compilado
│   └── DeskEvidence.exe           # Executável portátil standalone (zero dependências)
├── tests/                         # Testes automatizados (unittest)
│   ├── test_config.py
│   ├── test_ticket.py
│   ├── test_hotkey_parser.py
│   ├── test_capture.py
│   └── test_annotation.py
└── deskevidence/                  # Pacote modular da aplicação
    ├── __init__.py
    ├── main.py                    # Ponto de entrada, Single-Instance Lock e orquestração
    ├── core/                      # Regras de negócio e integrações Windows
    │   ├── __init__.py
    │   ├── config_manager.py      # Persistência de preferências (JSON)
    │   ├── ticket_manager.py      # Gerenciamento de chamados e evidências
    │   ├── capture_engine.py      # Captura de janela ativa via Win32/DWM API
    │   ├── annotation_engine.py   # Motor de anotação de imagens e cópia para clipboard
    │   ├── hotkey_manager.py      # Escuta de atalhos globais via RegisterHotKey
    │   └── report_builder.py      # Construtor do relatório consolidado HTML
    ├── ui/                        # Interface visual moderna (CustomTkinter)
    │   ├── __init__.py
    │   ├── tray_controller.py     # Ícone e menu de contexto no System Tray
    │   ├── dialog_ticket.py       # Janela de criar, gerenciar e trocar chamados
    │   ├── dialog_editor.py       # Editor de evidências estilo Lightshot (marcações e recorte)
    │   ├── dialog_quick_note.py   # Popup ágil para breve anotação da evidência
    │   └── dialog_settings.py     # Painel de configurações do usuário
    └── assets/                    # Ícones e recursos visuais
        ├── generate_icons.py      # Script gerador dos ícones
        ├── icon.png / icon.ico
        └── icon_active.png / icon_active.ico
```

---

## 🚀 Formas de Executar

O DeskEvidence suporta diferentes formas de execução dependendo do perfil do usuário:

### 1. Modo Executável Portátil (Usuário Final / Sem Python) ⭐ RECOMENDADO
Se você deseja apenas usar o aplicativo ou enviá-lo para um colega:
- **Localização**: `dist\DeskEvidence.exe`
- **Como usar**: Dê um **duplo clique** no arquivo `DeskEvidence.exe`.
- **Zero Requisitos**: O computador **não precisa de Python instalado**, nem de privilégios de administrador. É uma aplicação standalone completa (~17 MB) que roda direto no System Tray.

### 2. Modo Desenvolvimento Local (Máquina Atual)
- Dê um duplo clique em **`run.bat`** (ou execute no PowerShell `./run.ps1`).
- O script utiliza o ambiente virtual `.venv` local e inicializa o app em segundo plano.

### 3. Modo Auto-Instalador (Código-Fonte em Outro Computador)
Se você clonou ou baixou o código-fonte em outro computador que possua Python:
- Dê um duplo clique em **`instalar_e_executar.bat`**.
- O script verifica o ambiente, cria automaticamente o `.venv` local no destino, instala as dependências de `requirements.txt` e inicia o aplicativo sem intervenção manual.

---

## 📦 Como Enviar / Distribuir para Outro Computador

| Cenário de Envio | Como Proceder | Vantagens |
| :--- | :--- | :--- |
| **Para usuários finais / colegas (Recomendado)** | Envie apenas o arquivo **`dist\DeskEvidence.exe`** (via Teams, Pen Drive, Rede ou compactado em `.zip`). | O destinatário só precisa dar duplo clique. Não requer Python, pip, permissões de admin nem dependências. |
| **Para desenvolvedores (Código-Fonte)** | Envie a pasta do projeto **SEM a pasta `.venv`**. O destinatário dá duplo clique em **`instalar_e_executar.bat`**. | O script cria o ambiente virtual localmente e instala as dependências de forma limpa e automática. |

> [!IMPORTANT]
> **Atenção:** Nunca copie a pasta `.venv` diretamente para outro computador. Ambientes virtuais Python registram caminhos absolutos da máquina de origem e não funcionam se movidos de computador. Para isso, use o executável standalone (`DeskEvidence.exe`) ou o script `instalar_e_executar.bat`.

### Como Gerar um Novo Executável (`.exe`)
Sempre que fizer alterações no código e quiser gerar uma nova versão compilada:
1. Dê um duplo clique em **`build_exe.bat`**.
2. O script executará o PyInstaller com todas as configurações de temas, ícones e dependências embutidas, gerando o novo `dist\DeskEvidence.exe`.

---

## ⌨️ Atalhos Padrão de Teclado

| Ação | Atalho Padrão | Descrição |
| :--- | :---: | :--- |
| **Capturar Evidência** | `Ctrl + Shift + E` | Tira o screenshot da janela ativa atual e abre o popup de nota. |
| **Ação de Chamado** | `Ctrl + Shift + P` | Abre criação de chamado (se nenhum ativo) ou gerencia/finaliza o ativo. |
| **Trocar Chamado** | `Ctrl + Shift + T` | Lista o histórico de chamados para alternar rapidamente. |
| **Configurações** | `Ctrl + Shift + C` | Abre a tela para personalizar atalhos, pastas e modo de captura. |

*Todos os atalhos podem ser personalizados a qualquer momento através do menu do System Tray -> **Configurações...**.*

---

## 📊 Estrutura de Pastas Gerada para os Chamados

Por padrão, o DeskEvidence salva os dados em `%USERPROFILE%\Documents\DeskEvidence_Evidencias` (ou na pasta que você selecionar nas configurações):

```
DeskEvidence_Evidencias/
└── [INC12345] - Validacao Homologacao SPED/
    ├── ticket.json                  # Metadados e catálogo do chamado
    ├── relatorio_evidencias.html    # Relatório executivo completo
    └── evidencias/
        ├── 001_20260914_084510_chrome.png
        ├── 002_20260914_084722_sap.png
        └── 003_20260914_085005_excel.png
```

---

## 🧪 Executando os Testes Automatizados

Para validar o funcionamento dos módulos:
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```

---

## 🛡️ Segurança e Conformidade Corporativa

Desenvolvido para atender aos padrões rigorosos de segurança corporativa (como em órgãos públicos e fazendários):
- **Sem Hooks de Teclado Globais (`WH_KEYBOARD_LL`)**: Evita bloqueios por soluções de antivírus e EDR corporativos.
- **Isolamento de Ambiente**: Utiliza ambiente virtual (`.venv`) local sem interferir em outras ferramentas do sistema operacional.
- **Privacidade**: Processamento e armazenamento 100% locais; nenhuma imagem ou informação é enviada para a rede.
