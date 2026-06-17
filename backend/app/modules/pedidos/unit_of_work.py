# app/modules/pedidos/unit_of_work.py
"""
UnitOfWork del módulo pedidos.


"""
from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.direcciones.repository import DireccionRepository
from app.modules.historial_estados_pedido.repository import HistorialRepository
from app.modules.ingredientes.repository import IngredienteRepository
from app.modules.pedidos.repository import CatalogoRepository, PedidoRepository
from app.modules.productos.repository import ProductoRepository


class PedidoUnitOfWork(UnitOfWork):
    """
    UoW del módulo pedidos.
    Expone:
    - pedidos:      operaciones sobre Pedido y DetallePedido
    - catalogos:    lectura de FormaPago y EstadoPedido
    - productos:    validación y modificación de stock 
    - ingredientes: validación y modificación de stock de ingredientes 
    - historial:    INSERT append-only de HistorialEstadoPedido 
    - direcciones:  lectura de DireccionEntrega para snapshot al crear pedido
    """

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.pedidos     = PedidoRepository(session)
        self.catalogos   = CatalogoRepository(session)
        self.productos   = ProductoRepository(session)
        self.ingredientes = IngredienteRepository(session)   
        self.historial   = HistorialRepository(session)      
        self.direcciones = DireccionRepository(session)
