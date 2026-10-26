export default function Panel({ title, action, children }) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2 className="text-sm font-semibold text-gray-800">{title}</h2>
        {action}
      </header>
      {children}
    </section>
  )
}
