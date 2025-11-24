# from django.db import models
# from audio_process.models import SpeakerSegment

# class LogicalResult(models.Model):
#     segment = models.OneToOneField(
#         SpeakerSegment,
#         on_delete=models.CASCADE,
#         related_name='logical_analysis'
#     )

#     speech_speed = models.FloatField(null=True, blank=True)
#     pause_duration = models.FloatField(null=True, blank=True)
#     is_overlap = models.BooleanField(default=False)

#     profanity_score = models.FloatField(null=True, blank=True)
#     threat_score = models.FloatField(null=True, blank=True)
#     insistence_score = models.FloatField(null=True, blank=True)
#     intent_label = models.CharField(max_length=100, null=True, blank=True)

#     manual_compliance_score = models.FloatField(null=True, blank=True)
#     empathy_score = models.FloatField(null=True, blank=True)

#     context_appropriateness = models.FloatField(null=True, blank=True)

#     class Meta:
#         db_table = 'logical_results'
#         ordering = ['segment__start_time']