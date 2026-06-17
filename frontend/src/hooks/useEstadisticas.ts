// src/hooks/useEstadisticas.ts
import { useQuery } from '@tanstack/react-query'
import { qk } from '../queries/keys'
import {
  getResumenApi, getVentasApi, getProductosTopApi,
  getPedidosPorEstadoApi, getIngresosApi,
} from '../api/estadisticas'

const STALE = 60_000

export const useResumen = () =>
  useQuery({ queryKey: qk.estadisticas.resumen, queryFn: getResumenApi, staleTime: STALE })

export const useVentas = (desde?: string, hasta?: string, agrupacion = 'day') =>
  useQuery({
    queryKey: qk.estadisticas.ventas(desde, hasta, agrupacion),
    queryFn: () => getVentasApi(desde, hasta, agrupacion),
    staleTime: STALE,
  })

export const useProductosTop = (limit = 10) =>
  useQuery({
    queryKey: qk.estadisticas.productosTop(limit),
    queryFn: () => getProductosTopApi(limit),
    staleTime: STALE,
  })

export const usePedidosPorEstado = () =>
  useQuery({
    queryKey: qk.estadisticas.pedidosPorEstado,
    queryFn: getPedidosPorEstadoApi,
    staleTime: STALE,
  })

export const useIngresos = (desde?: string, hasta?: string) =>
  useQuery({
    queryKey: qk.estadisticas.ingresos(desde, hasta),
    queryFn: () => getIngresosApi(desde, hasta),
    staleTime: STALE,
  })
