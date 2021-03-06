import pytest
import torch

from pytorch_lightning import Trainer
from tests.base import EvalModelTemplate


@pytest.mark.parametrize('max_steps', [1, 2, 3])
def test_on_before_zero_grad_called(max_steps):

    class CurrentTestModel(EvalModelTemplate):
        on_before_zero_grad_called = 0

        def on_before_zero_grad(self, optimizer):
            self.on_before_zero_grad_called += 1

    model = CurrentTestModel()

    trainer = Trainer(
        max_steps=max_steps,
        num_sanity_val_steps=5,
    )
    assert 0 == model.on_before_zero_grad_called
    trainer.fit(model)
    assert max_steps == model.on_before_zero_grad_called

    model.on_before_zero_grad_called = 0
    trainer.test(model)
    assert 0 == model.on_before_zero_grad_called


def test_training_epoch_end_metrics_collection(tmpdir):
    """ Test that progress bar metrics also get collected at the end of an epoch. """
    num_epochs = 3

    class CurrentModel(EvalModelTemplate):

        def training_step(self, *args, **kwargs):
            output = super().training_step(*args, **kwargs)
            output['progress_bar'].update({'step_metric': torch.tensor(-1)})
            output['progress_bar'].update({'shared_metric': 100})
            return output

        def training_epoch_end(self, outputs):
            epoch = self.current_epoch
            # both scalar tensors and Python numbers are accepted
            return {
                'progress_bar': {
                    f'epoch_metric_{epoch}': torch.tensor(epoch),  # add a new metric key every epoch
                    'shared_metric': 111,
                }
            }

    model = CurrentModel()
    trainer = Trainer(
        max_epochs=num_epochs,
        default_root_dir=tmpdir,
        overfit_pct=0.1,
    )
    result = trainer.fit(model)
    assert result == 1
    metrics = trainer.progress_bar_dict

    # metrics added in training step should be unchanged by epoch end method
    assert metrics['step_metric'] == -1
    # a metric shared in both methods gets overwritten by epoch_end
    assert metrics['shared_metric'] == 111
    # metrics are kept after each epoch
    for i in range(num_epochs):
        assert metrics[f'epoch_metric_{i}'] == i
