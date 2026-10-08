import { useState } from 'react'

type Plate = {
  text: string
  format: 'old' | 'mercosul'
  confidence: number
  box: [number, number, number, number]
}

type ImageInfo = { url: string; width: number; height: number }

export default function App() {
  const [image, setImage] = useState<ImageInfo | null>(null)
  const [plates, setPlates] = useState<Plate[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [elapsedMs, setElapsedMs] = useState<number | null>(null)

  async function handleFile(file: File) {
    if (image) URL.revokeObjectURL(image.url)
    setImage(null)
    setPlates(null)
    setError(null)
    setElapsedMs(null)

    // The API returns boxes in original pixels; the browser applies EXIF orientation like the API does.
    const url = URL.createObjectURL(file)
    const bitmap = await createImageBitmap(file)
    setImage({ url, width: bitmap.width, height: bitmap.height })
    bitmap.close()

    const body = new FormData()
    body.append('image', file)
    setLoading(true)
    const start = performance.now()
    try {
      const response = await fetch('/v1/plates/read', { method: 'POST', body })
      if (!response.ok) {
        const detail = await response.json().catch(() => null)
        throw new Error(detail?.detail ?? `Erro ${response.status}`)
      }
      const data: { plates: Plate[] } = await response.json()
      setPlates(data.plates)
      setElapsedMs(performance.now() - start)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <h1>Teste de leitura de placa</h1>
      <input
        type="file"
        accept="image/*"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFile(file)
        }}
      />

      {loading && <p>Lendo…</p>}
      {error && <p className="error">{error}</p>}

      {plates && (
        <>
          <p>
            {plates.length === 0 ? 'Nenhuma placa encontrada.' : `${plates.length} placa(s) encontrada(s).`}
            {elapsedMs !== null && ` (${Math.round(elapsedMs)} ms)`}
          </p>
          {plates.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Placa</th>
                  <th>Formato</th>
                  <th>Confiança</th>
                </tr>
              </thead>
              <tbody>
                {plates.map((plate, i) => (
                  <tr key={i}>
                    <td>
                      <strong>{plate.text}</strong>
                    </td>
                    <td>{plate.format}</td>
                    <td>{(plate.confidence * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {image && (
        <div className="preview">
          <img src={image.url} alt="Foto enviada" />
          {plates?.map(({ box: [x1, y1, x2, y2] }, i) => (
            <div
              key={i}
              className="box"
              style={{
                left: `${(x1 / image.width) * 100}%`,
                top: `${(y1 / image.height) * 100}%`,
                width: `${((x2 - x1) / image.width) * 100}%`,
                height: `${((y2 - y1) / image.height) * 100}%`,
              }}
            />
          ))}
        </div>
      )}
    </main>
  )
}
