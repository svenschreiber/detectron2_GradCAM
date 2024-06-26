from .gradcam import GradCAM, GradCamPlusPlus
import detectron2.data.transforms as T
import torch
from detectron2.checkpoint import DetectionCheckpointer
from detectron2.config import get_cfg
from detectron2.data import DatasetCatalog, MetadataCatalog
from detectron2.data.detection_utils import read_image
from detectron2.modeling import build_model
from detectron2.data.datasets import register_coco_instances

class Detectron2GradCAM():
  """
      Attributes
    ----------
    cfg : CfgNode
        detectron2 model config
    model : detectron2 GeneralizedRCNN Model
        A model using the detectron2 API for inferencing
    """
  def __init__(self, cfg, model):
      self.cfg =  cfg
      self.model = model

  def _set_input_image(self, image):
      self.image = image
      self.image_height, self.image_width = self.image.shape[:2]
      transform_gen = T.ResizeShortestEdge(
          [self.cfg.INPUT.MIN_SIZE_TEST, self.cfg.INPUT.MIN_SIZE_TEST], self.cfg.INPUT.MAX_SIZE_TEST
      )
      transformed_img = transform_gen.get_transform(self.image).apply_image(self.image)
      self.input_tensor = torch.as_tensor(transformed_img.astype("float32").transpose(2, 0, 1)).requires_grad_(True)
  
  def get_cam(self, image, target_instance, layer_name, grad_cam_instance):
      """
      Calls the GradCAM instance

      Parameters
      ----------
      image: numpy.ndarray
          inference image
      target_instance : int
          The target instance index
      layer_name : str
          Convolutional layer to perform GradCAM on
      grad_cam_type : str
          GradCAM or GradCAM++ (for multiple instances of the same object, GradCAM++ can be favorable)

      Returns
      -------
      image_dict : dict
        {"image" : <image>, "cam" : <cam>, "output" : <output>, "label" : <label>}
        <image> original input image
        <cam> class activation map resized to original image shape
        <output> instances object generated by the model
        <label> label of the 
      cam_orig : numpy.ndarray
        unprocessed raw cam
      """
      self._set_input_image(image)
      input_image_dict = {"image": self.input_tensor, "height": self.image_height, "width": self.image_width}
      grad_cam = grad_cam_instance(self.model, layer_name)
    
      with grad_cam as cam:
        cam, cam_orig, output = cam(input_image_dict, target_instance=target_instance)
      
      output_dict = self.get_output_dict(cam, output, target_instance)
      
      return output_dict, cam_orig
    
  def get_output_dict(self, cam, output, target_instance):
      image_dict = {}
      image_dict["image"] =  self.image
      image_dict["cam"] = cam
      image_dict["output"] = output
      image_dict["label"] = MetadataCatalog.get(self.cfg.DATASETS.TRAIN[0]).thing_classes[output["instances"].pred_classes[target_instance]]
      return image_dict
