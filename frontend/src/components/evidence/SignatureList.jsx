import { useState } from 'react'
import { useWorkOrderSignatures } from '../../api/evidence'

function formatDateCO(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-CO', { timeZone: 'America/Bogota' })
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="ml-2 text-xs text-brand hover:underline shrink-0"
    >
      {copied ? 'Copiado' : 'Copiar hash'}
    </button>
  )
}

function SignatureSkeleton() {
  return (
    <div className="flex gap-4 p-4 border border-gray-100 rounded-lg animate-pulse">
      <div className="h-16 w-32 bg-gray-200 rounded" />
      <div className="flex-1 space-y-2">
        <div className="h-3 bg-gray-200 rounded w-1/2" />
        <div className="h-3 bg-gray-200 rounded w-1/3" />
        <div className="h-3 bg-gray-200 rounded w-2/3" />
      </div>
    </div>
  )
}

export default function SignatureList({ workOrderId }) {
  const { data: signatures = [], isLoading, isError } = useWorkOrderSignatures(workOrderId)

  if (isLoading) {
    return (
      <div className="space-y-3">
        <SignatureSkeleton />
      </div>
    )
  }

  if (isError) {
    return <p className="text-sm text-red-400">Error al cargar las firmas.</p>
  }

  if (!signatures.length) {
    return <p className="text-sm text-gray-500">Aun no hay firmas registradas.</p>
  }

  return (
    <div className="space-y-3">
      {signatures.map((sig) => (
        <div
          key={sig.id}
          className="flex flex-col sm:flex-row items-start gap-4 p-4 border border-gray-100 rounded-lg"
        >
          <img
            src={sig.file_url}
            alt="Firma digital"
            className="h-16 w-auto border border-gray-200 rounded bg-white object-contain"
          />
          <div className="space-y-0.5 text-sm min-w-0">
            <p className="font-medium text-gray-800">{sig.signer_name}</p>
            {sig.signer_role && (
              <p className="text-xs text-gray-500">{sig.signer_role}</p>
            )}
            <p className="text-xs text-gray-500">
              {sig.signature_type === 'TECHNICIAN' ? 'Tecnico' : 'Cliente'}
            </p>
            <p className="text-xs text-gray-500">{formatDateCO(sig.signed_at || sig.created_at)}</p>
            {sig.hash_sha256 && (
              <div className="flex items-center min-w-0">
                <span className="font-mono text-xs text-gray-500">
                  {sig.hash_sha256.slice(0, 12)}...
                </span>
                <CopyButton text={sig.hash_sha256} />
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
