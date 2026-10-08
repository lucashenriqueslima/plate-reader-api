# plate-reader-api

API HTTP que recebe uma foto e devolve o texto das placas brasileiras que estão nela, tanto
no padrão antigo (`ABC1234`) quanto no Mercosul (`BRA2E19`), de carro ou de moto (duas linhas).
O caso para o qual a API foi feita é foto de celular tirada de perto.

## Como funciona

1. **Detector** YOLOv9 já treinado para placas
   ([open-image-models](https://github.com/ankandrew/open-image-models), modelo padrão
   `yolo-v9-t-384-license-plate-end2end`) acha cada placa na foto.
2. **OCR** [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr) (modelo padrão
   `cct-s-v2-global-model`, que inclui o Brasil entre os países do treino) devolve, para cada
   uma das 10 posições, a probabilidade de cada caractere.
3. **Regras brasileiras** ([brazilian_plate.py](src/plate_reader_api/brazilian_plate.py)):
   escolhe a leitura mais provável que respeita o formato `LLLNLNN` (Mercosul) ou `LLLNNNN`
   (antiga). Letra nunca sai em posição de número e vice-versa, o que resolve trocas como 0/O e 8/B.

Tudo roda em ONNX Runtime, em CPU, sem GPU.

### Por que esta stack

- **Ultralytics (YOLO11/YOLO26) ficou de fora** porque a licença AGPL-3.0 também cobre os
  modelos treinados; numa API fechada ela exige a licença Enterprise paga.
- **Os datasets acadêmicos brasileiros** (UFPR-ALPR, RodoSol-ALPR) proíbem uso comercial,
  então não podem ser usados no treino.
- **Pesos pré-treinados só no piloto:** o código do fast-plate-ocr e do open-image-models é
  MIT, mas o autor não declara a origem dos dados de treino dos pesos. Antes da produção, o
  plano é treinar o nosso OCR com dados próprios.

## Rodar

```bash
uv sync
uv run uvicorn plate_reader_api.main:app --port 8000
```

Ou com Docker (os modelos padrão já vão embutidos na imagem):

```bash
docker build -t plate-reader-api .
docker run -p 8000:8000 plate-reader-api
```

Para trocar de modelo, use as variáveis `DETECTOR_MODEL` e `OCR_MODEL`.

## API

```bash
curl -F image=@foto.jpg http://localhost:8000/v1/plates/read
```

```json
{
  "plates": [
    { "text": "BRA2E19", "format": "mercosul", "confidence": 0.98, "box": [412, 530, 690, 640] }
  ]
}
```

- `plates` vem ordenado da leitura mais confiável para a menos confiável, e fica vazio quando
  nenhuma placa é encontrada.
- `confidence` é a menor probabilidade entre os 7 caracteres (e as posições que deveriam
  estar vazias). Quem chama a API deve descartar leituras abaixo de um limite, escolhido a
  partir do benchmark.
- `box` é a posição da placa na foto, em pixels: `[x1, y1, x2, y2]`.
- Arquivo que não é imagem retorna `422`.
- A orientação EXIF da foto é respeitada.

## Testar pelo navegador

Com a API rodando na porta 8000, em outro terminal:

```bash
cd web
npm install
npm run dev
```

Abra http://localhost:5173 e envie uma foto. A página mostra as placas lidas e desenha a
caixa de cada uma sobre a foto. O Vite encaminha `/v1` para `localhost:8000`.

## Benchmark

Monte uma pasta com as fotos e um `labels.csv`:

```csv
image_path,plate_text
fotos/001.jpg,BRA2E19
fotos/002.jpg,ABC1234
```

`plate_text` é o que está **impresso na placa da foto**. Se um carro com placa antiga
cadastrada já trocou para a Mercosul, o rótulo é o da Mercosul.

```bash
uv run python scripts/benchmark.py caminho/labels.csv
uv run python scripts/benchmark.py caminho/labels.csv --detector-model yolo-v9-t-640-license-plate-end2end --ocr-model cct-xs-v2-global-model
```

O relatório mostra:
- acerto exato (7/7), no total e separado entre placa antiga e Mercosul;
- fotos em que nenhuma placa foi encontrada;
- latência média e p95;
- uma tabela de limite de confiança × cobertura × acerto, usada para escolher o limite;
- a lista de erros.

## Próximos passos

1. Rodar o benchmark com fotos reais (cerca de 300, cobrindo carro/moto e antiga/Mercosul).
2. Se o acerto ficar abaixo da meta, treinar o OCR (7 posições, alfabeto `0-9A-Z`) com
   recortes das nossas fotos mais placas sintéticas, e trocar via `OCR_MODEL`.
