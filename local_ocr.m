#import <Foundation/Foundation.h>
#import <Vision/Vision.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSMutableDictionary *results = [NSMutableDictionary dictionary];
        for (int i = 1; i < argc; i++) {
            NSString *path = [NSString stringWithUTF8String:argv[i]];
            VNRecognizeTextRequest *request = [VNRecognizeTextRequest new];
            request.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
            request.recognitionLanguages = @[@"zh-Hans", @"en-US"];
            request.usesLanguageCorrection = YES;
            NSError *error = nil;
            VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithURL:[NSURL fileURLWithPath:path] options:@{}];
            NSMutableArray *lines = [NSMutableArray array];
            if ([handler performRequests:@[request] error:&error]) {
                for (VNRecognizedTextObservation *observation in request.results) {
                    VNRecognizedText *candidate = [[observation topCandidates:1] firstObject];
                    if (candidate.string.length) [lines addObject:candidate.string];
                }
            } else if (error) {
                fprintf(stderr, "OCR failed: %s\n", error.localizedDescription.UTF8String);
                return 2;
            }
            results[path] = lines;
        }
        NSData *json = [NSJSONSerialization dataWithJSONObject:results options:0 error:nil];
        if (!json) return 1;
        fwrite(json.bytes, 1, json.length, stdout);
    }
    return 0;
}
