from dcc.core.gpu import Capabilities
from dcc.ui.widgets.inputs import NoWheelComboBox


class GpuSelector(NoWheelComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)

    def populate(self, capabilities: Capabilities, prefer: str = ""):
        self.clear()
        for gpu in capabilities.gpus:
            self.addItem(f"{gpu.vendor.value} - {gpu.name}", gpu.vendor.value)
        # CPU-only fallback is always selectable even when a GPU is present
        if "CPU" not in [self.itemData(i) for i in range(self.count())]:
            self.addItem("CPU (software encoding only)", "CPU")

        if prefer:
            idx = self.findData(prefer)
            if idx >= 0:
                self.setCurrentIndex(idx)

    def current_vendor(self) -> str:
        return self.currentData() or ""
