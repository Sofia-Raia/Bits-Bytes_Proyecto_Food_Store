// src/pages/usuarios/UsuariosPage.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../store/authStore'
import { Navigate } from 'react-router-dom'
import Modal from '../../components/ui/Modal'
import ConfirmDialog from '../../components/ui/ConfirmDialog'
import Pagination from '../../components/ui/Pagination'
import Toast, { useToast } from '../../components/ui/Toast'
import { SkeletonRow } from '../../components/ui/Skeleton'
import { listarUsuariosApi, crearUsuarioApi, editarUsuarioApi, desactivarUsuarioApi, reactivarUsuarioApi } from '../../api/auth'
import type { UsuarioListItem, UsuarioUpdate } from '../../api/auth'
import type { RolCodigo } from '../../models/auth'
import { qk } from '../../queries/keys'

const PAGE_SIZE = 10
const ROLES_DISPONIBLES: RolCodigo[] = ['ADMIN', 'STOCK', 'PEDIDOS', 'CLIENT']
type SortBy  = 'nombre' | 'apellido' | 'email' | 'created_at'
type SortDir = 'asc' | 'desc'

const rolColor: Record<string, string> = {
  ADMIN:   'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  STOCK:   'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  PEDIDOS: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  CLIENT:  'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
}

interface FormState { nombre: string; apellido: string; email: string; celular: string; password: string; roles: RolCodigo[] }
const emptyForm = (): FormState => ({ nombre: '', apellido: '', email: '', celular: '', password: '', roles: [] })

function SortableTh({ label, field, sortBy, sortDir, onSort }: { label: string; field: SortBy; sortBy: SortBy; sortDir: SortDir; onSort: (f: SortBy) => void }) {
  const active = sortBy === field
  return (
    <th className="text-left px-5 py-3 font-semibold text-gray-600 dark:text-gray-300 cursor-pointer select-none hover:text-gray-800 dark:hover:text-gray-100 group" onClick={() => onSort(field)}>
      <span className="inline-flex items-center gap-1">
        {label}
        <span className={`text-xs transition-opacity ${active ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`}>{active ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}</span>
      </span>
    </th>
  )
}

export default function UsuariosPage() {
  const { user } = useAuth()
  if (!user?.roles.includes('ADMIN')) return <Navigate to="/ingredientes" replace />

  const qc = useQueryClient()

  const [page,             setPageState]        = useState(1)
  const [incluirInactivos, setIncluirInactivos] = useState(false)
  const [busqueda,         setBusqueda]         = useState('')
  const [sortBy,           setSortBy]           = useState<SortBy>('nombre')
  const [sortDir,          setSortDir]          = useState<SortDir>('asc')
  const [modalOpen,        setModalOpen]        = useState(false)
  const [editTarget,       setEditTarget]       = useState<UsuarioListItem | null>(null)
  const [deleteTarget,     setDeleteTarget]     = useState<UsuarioListItem | null>(null)
  const [form,             setForm]             = useState<FormState>(emptyForm())
  const [formError,        setFormError]        = useState('')
  const [formDirty,        setFormDirty]        = useState(false)
  const [confirmDiscard,   setConfirmDiscard]   = useState(false)
  const [actionLoadingId,  setActionLoadingId]  = useState<number | null>(null)

  const { toasts, addToast, removeToast } = useToast()

  const listQuery = useQuery({
    queryKey: qk.usuarios.list({ page, busqueda, sortBy, sortDir, incluirInactivos }),
    queryFn: () => listarUsuariosApi(
      incluirInactivos, busqueda || undefined,
      page, PAGE_SIZE, sortBy, sortDir,
    ),
  })

  const usuarios: UsuarioListItem[] = listQuery.data?.items ?? []
  const total = listQuery.data?.total ?? 0
  const loading = listQuery.isFetching
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const invalidar = () => qc.invalidateQueries({ queryKey: qk.usuarios.all })

  const setPage = (n: number) => setPageState(Math.max(1, Math.min(n, totalPages)))
  const handleSort = (field: SortBy) => {
    const d: SortDir = sortBy === field && sortDir === 'asc' ? 'desc' : 'asc'
    setSortBy(field); setSortDir(d); setPageState(1)
  }

  const openNew = () => { setEditTarget(null); setForm(emptyForm()); setFormError(''); setFormDirty(false); setModalOpen(true) }
  const openEdit = (u: UsuarioListItem) => { setEditTarget(u); setForm({ nombre: u.nombre, apellido: u.apellido, email: u.email, celular: u.celular ?? '', password: '', roles: u.roles }); setFormError(''); setFormDirty(false); setModalOpen(true) }
  const updateForm = (updates: Partial<FormState>) => { setForm(f => ({ ...f, ...updates })); setFormDirty(true) }
  const requestClose = () => { if (formDirty) setConfirmDiscard(true); else setModalOpen(false) }
  const handleConfirmDiscard = () => { setConfirmDiscard(false); setModalOpen(false); setFormDirty(false) }

  const guardarMut = useMutation({
    mutationFn: async () => {
      if (editTarget) {
        const patch: UsuarioUpdate = { nombre: form.nombre || undefined, apellido: form.apellido || undefined, email: form.email || undefined, celular: form.celular || undefined, roles: form.roles }
        if (form.password) patch.password = form.password
        await editarUsuarioApi(editTarget.id, patch)
        return 'editar' as const
      }
      await crearUsuarioApi({ nombre: form.nombre, apellido: form.apellido, email: form.email, celular: form.celular || undefined, password: form.password, roles: form.roles })
      return 'crear' as const
    },
    onSuccess: (accion) => {
      addToast(accion === 'editar' ? 'Usuario actualizado' : 'Usuario creado', 'success')
      setModalOpen(false); setFormDirty(false)
      invalidar()
    },
    onError: (err: unknown) => setFormError(err instanceof Error ? err.message : 'Error al guardar'),
  })

  const desactivarMut = useMutation({
    mutationFn: (id: number) => desactivarUsuarioApi(id),
    onSuccess: () => { if (deleteTarget) addToast(`"${deleteTarget.nombre}" desactivado`, 'success'); invalidar() },
    onError: (err: unknown) => addToast(err instanceof Error ? err.message : 'Error', 'error'),
    onSettled: () => setDeleteTarget(null),
  })

  const reactivarMut = useMutation({
    mutationFn: (id: number) => reactivarUsuarioApi(id),
    onSuccess: (_res, id) => {
      const u = usuarios.find(x => x.id === id)
      addToast(`"${u?.nombre ?? 'Usuario'}" reactivado`, 'success')
      invalidar()
    },
    onError: (err: unknown) => addToast(err instanceof Error ? err.message : 'Error', 'error'),
    onSettled: () => setActionLoadingId(null),
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setFormError('')
    if (!editTarget && !form.password) { setFormError('La contraseña es obligatoria'); return }
    await guardarMut.mutateAsync().catch(() => { /* error vía onError */ })
  }

  const handleDesactivar = async () => {
    if (!deleteTarget) return
    await desactivarMut.mutateAsync(deleteTarget.id).catch(() => { /* error vía onError */ })
  }

  const handleReactivar = (u: UsuarioListItem) => {
    setActionLoadingId(u.id)
    reactivarMut.mutate(u.id)
  }

  const toggleRol = (rol: RolCodigo) => { updateForm({ roles: form.roles.includes(rol) ? form.roles.filter(r => r !== rol) : [...form.roles, rol] }) }

  const formLoading = guardarMut.isPending
  const confirmLoading = desactivarMut.isPending

  const inputCls = "w-full border border-gray-300 dark:border-gray-600 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
  const labelCls = "block text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1"

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">👥 Usuarios</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{total} usuario{total !== 1 ? 's' : ''}</p>
        </div>
        <button onClick={openNew} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-xl transition">+ Nuevo usuario</button>
      </div>

      <div className="flex flex-wrap gap-3 mb-6 items-center">
        <input type="search" placeholder="Buscar por nombre, apellido o email..." value={busqueda}
          onChange={e => { setBusqueda(e.target.value); setPageState(1) }}
          className="flex-1 sm:max-w-sm border border-gray-300 dark:border-gray-600 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-400 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500" />
        <label className="flex items-center gap-2 cursor-pointer select-none bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl px-4 py-2.5 hover:bg-gray-100 dark:hover:bg-gray-600 transition">
          <input type="checkbox" checked={incluirInactivos} onChange={e => { setIncluirInactivos(e.target.checked); setPageState(1) }} className="w-4 h-4 accent-gray-500" />
          <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Mostrar inactivos</span>
        </label>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700">
            <tr>
              <SortableTh label="Nombre"   field="nombre"   sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
              <SortableTh label="Apellido" field="apellido" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
              <SortableTh label="Email"    field="email"    sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
              <th className="text-left px-5 py-3 font-semibold text-gray-600 dark:text-gray-300">Roles</th>
              <th className="text-left px-5 py-3 font-semibold text-gray-600 dark:text-gray-300">Estado</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
            {loading && Array.from({ length: PAGE_SIZE }).map((_, i) => <SkeletonRow key={i} cols={6} />)}
            {!loading && usuarios.length === 0 && (
              <tr><td colSpan={6} className="text-center py-16 text-gray-400 dark:text-gray-500"><p className="text-4xl mb-2">👥</p><p>No hay usuarios</p></td></tr>
            )}
            {!loading && usuarios.map(u => (
              <tr key={u.id} className={`hover:bg-gray-50 dark:hover:bg-gray-700/40 transition ${!u.activo ? 'opacity-50' : ''}`}>
                <td className="px-5 py-3 font-medium text-gray-800 dark:text-gray-200">{u.nombre}</td>
                <td className="px-5 py-3 text-gray-700 dark:text-gray-300">{u.apellido}</td>
                <td className="px-5 py-3 text-gray-600 dark:text-gray-400">{u.email}</td>
                <td className="px-5 py-3">
                  <div className="flex flex-wrap gap-1">
                    {u.roles.length === 0
                      ? <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">Sin rol</span>
                      : u.roles.map(r => <span key={r} className={`text-xs px-2 py-0.5 rounded-full font-medium ${rolColor[r] ?? 'bg-gray-100 text-gray-700'}`}>{r}</span>)
                    }
                  </div>
                </td>
                <td className="px-5 py-3">
                  <span className={`text-xs font-semibold px-2 py-1 rounded-full ${u.activo ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-300'}`}>
                    {u.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <div className="flex gap-2 justify-end">
                    {u.activo ? (
                      <>
                        <button onClick={() => openEdit(u)} disabled={actionLoadingId === u.id}
                          className="text-xs bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-100 dark:hover:bg-blue-900/50 text-blue-700 dark:text-blue-300 font-semibold px-3 py-1.5 rounded-lg transition disabled:opacity-40">Editar</button>
                        <button onClick={() => setDeleteTarget(u)} disabled={actionLoadingId === u.id}
                          className="text-xs bg-red-50 dark:bg-red-900/30 hover:bg-red-100 dark:hover:bg-red-900/50 text-red-600 dark:text-red-300 font-semibold px-3 py-1.5 rounded-lg transition disabled:opacity-40">Desactivar</button>
                      </>
                    ) : (
                      <button onClick={() => handleReactivar(u)} disabled={actionLoadingId === u.id}
                        className="text-xs bg-green-50 dark:bg-green-900/30 hover:bg-green-100 dark:hover:bg-green-900/50 text-green-700 dark:text-green-300 font-semibold px-3 py-1.5 rounded-lg transition disabled:opacity-40 min-w-[72px]">
                        {actionLoadingId === u.id ? <span className="flex items-center gap-1 justify-center"><svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" /></svg></span> : 'Reactivar'}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-5 pb-4">
          <Pagination page={page} totalPages={totalPages} total={total} pageSize={PAGE_SIZE} onPage={setPage} loading={loading} />
        </div>
      </div>

      <Modal open={modalOpen} onClose={requestClose} title={editTarget ? 'Editar usuario' : 'Nuevo usuario'}>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <div><label className={labelCls}>Nombre *</label><input type="text" required value={form.nombre} onChange={e => updateForm({ nombre: e.target.value })} className={inputCls} /></div>
            <div><label className={labelCls}>Apellido *</label><input type="text" required value={form.apellido} onChange={e => updateForm({ apellido: e.target.value })} className={inputCls} /></div>
          </div>
          <div><label className={labelCls}>Email *</label><input type="email" required value={form.email} onChange={e => updateForm({ email: e.target.value })} className={inputCls} /></div>
          <div><label className={labelCls}>Celular</label><input type="tel" value={form.celular} onChange={e => updateForm({ celular: e.target.value })} className={inputCls} /></div>
          <div>
            <label className={labelCls}>Contraseña {editTarget ? '(dejar vacío para no cambiar)' : '*'}</label>
            <input type="password" value={form.password} required={!editTarget} onChange={e => updateForm({ password: e.target.value })} className={inputCls} />
          </div>
          <div>
            <label className={labelCls}>Roles</label>
            <div className="flex flex-wrap gap-2">
              {ROLES_DISPONIBLES.map(rol => (
                <button key={rol} type="button" onClick={() => toggleRol(rol)}
                  className={`text-xs font-semibold px-3 py-1.5 rounded-full border-2 transition ${form.roles.includes(rol) ? `${rolColor[rol]} border-current` : 'bg-gray-50 dark:bg-gray-700 text-gray-400 dark:text-gray-500 border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'}`}>
                  {rol}
                </button>
              ))}
            </div>
            {form.roles.length === 0 && <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Sin roles asignados → solo lectura</p>}
          </div>
          {formError && <p className="text-sm text-red-500 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg px-3 py-2">{formError}</p>}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={requestClose} className="px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition text-sm font-medium">Cancelar</button>
            <button type="submit" disabled={formLoading} className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition disabled:opacity-50">
              {formLoading ? 'Guardando...' : editTarget ? 'Guardar cambios' : 'Crear usuario'}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog open={confirmDiscard} title="¿Descartar cambios?" message="Tenés cambios sin guardar. Si cerrás ahora, se van a perder." confirmLabel="Descartar" danger onConfirm={handleConfirmDiscard} onCancel={() => setConfirmDiscard(false)} />
      <ConfirmDialog open={!!deleteTarget} title="¿Desactivar usuario?" message={`"${deleteTarget?.nombre} ${deleteTarget?.apellido}" quedará inactivo y no podrá iniciar sesión.`} confirmLabel="Desactivar" danger loading={confirmLoading} onConfirm={handleDesactivar} onCancel={() => !confirmLoading && setDeleteTarget(null)} />
      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  )
}
