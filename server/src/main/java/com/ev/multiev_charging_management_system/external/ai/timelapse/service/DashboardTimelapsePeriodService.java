package com.ev.multiev_charging_management_system.external.ai.timelapse.service;

import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseResponse;
import com.ev.multiev_charging_management_system.external.ai.timelapse.dto.DashboardTimelapseUpsertRequest;
import com.ev.multiev_charging_management_system.external.ai.timelapse.entity.DashboardTimelapsePeriod;
import com.ev.multiev_charging_management_system.external.ai.timelapse.entity.DashboardTimelapseStationFrame;
import com.ev.multiev_charging_management_system.external.ai.timelapse.repository.DashboardTimelapsePeriodRepository;
import com.ev.multiev_charging_management_system.external.ai.timelapse.repository.DashboardTimelapseStationFrameRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static org.springframework.http.HttpStatus.BAD_REQUEST;
import static org.springframework.http.HttpStatus.NOT_FOUND;

@Service
@RequiredArgsConstructor
public class DashboardTimelapsePeriodService {

    private final DashboardTimelapsePeriodRepository periodRepository;
    private final DashboardTimelapseStationFrameRepository frameRepository;

    @Transactional(readOnly = true)
    public List<DashboardTimelapseResponse.Summary> activePeriods() {
        return periodRepository.findByActiveTrueOrderByEndDateDescCreatedAtDesc()
                .stream()
                .map(this::toSummary)
                .toList();
    }

    @Transactional(readOnly = true)
    public DashboardTimelapseResponse.Detail latestActivePeriod() {
        DashboardTimelapsePeriod period = periodRepository.findTopByActiveTrueOrderByEndDateDescCreatedAtDesc()
                .orElseThrow(() -> new ResponseStatusException(NOT_FOUND, "Dashboard timelapse period not found."));
        return detail(period);
    }

    @Transactional(readOnly = true)
    public DashboardTimelapseResponse.Detail getPeriod(String periodKey) {
        DashboardTimelapsePeriod period = periodRepository.findByPeriodKey(periodKey)
                .orElseThrow(() -> new ResponseStatusException(NOT_FOUND, "Dashboard timelapse period not found."));
        return detail(period);
    }

    @Transactional
    public DashboardTimelapseResponse.Detail upsertPeriod(DashboardTimelapseUpsertRequest request) {
        validateRequest(request);
        DashboardTimelapsePeriod period = periodRepository.findByPeriodKey(request.periodKey())
                .orElseGet(() -> DashboardTimelapsePeriod.create(
                        request.periodKey(),
                        request.label(),
                        request.startDate(),
                        request.endDate(),
                        request.description(),
                        request.source(),
                        request.active() == null || request.active()
                ));
        period.update(
                request.periodKey(),
                request.label(),
                request.startDate(),
                request.endDate(),
                request.description(),
                request.source(),
                request.active() == null || request.active()
        );
        DashboardTimelapsePeriod savedPeriod = periodRepository.save(period);
        periodRepository.flush();

        frameRepository.deleteByPeriodId(savedPeriod.getId());
        frameRepository.flush();
        frameRepository.saveAll(toFrames(savedPeriod, request.frames()));
        return detail(savedPeriod);
    }

    @Transactional
    public void seedDefaultPeriodIfMissing() {
        String periodKey = "presentation-2022-jan-feb-transformer-lookahead";
        if (periodRepository.existsByPeriodKey(periodKey)) {
            return;
        }

        DashboardTimelapseUpsertRequest request = new DashboardTimelapseUpsertRequest(
                periodKey,
                "2022-02-14 EV Transformer 공유 대표 24h",
                LocalDate.parse("2022-02-14"),
                LocalDate.parse("2022-02-14"),
                "2022년 1-2월 평가 구간에서 15시 공유량, 낮 시간 PV, 피크 수요를 함께 고려해 고른 공유 시연용 대표 하루의 24시간 가속 재생 데이터.",
                "ev_transformer_shape_cal_lookahead_physical",
                true,
                buildDefaultFrames()
        );
        upsertPeriod(request);
    }

    private DashboardTimelapseResponse.Detail detail(DashboardTimelapsePeriod period) {
        List<DashboardTimelapseStationFrame> frames =
                frameRepository.findByPeriodIdOrderByFrameIndexAscStationIdAsc(period.getId());
        Map<Integer, List<DashboardTimelapseStationFrame>> byIndex = frames.stream()
                .collect(Collectors.groupingBy(
                        DashboardTimelapseStationFrame::getFrameIndex,
                        LinkedHashMap::new,
                        Collectors.toList()
                ));
        List<DashboardTimelapseResponse.Frame> responseFrames = byIndex.entrySet()
                .stream()
                .map(entry -> new DashboardTimelapseResponse.Frame(
                        entry.getKey(),
                        entry.getValue().get(0).getFrameDate(),
                        entry.getValue().get(0).getFrameHour(),
                        entry.getValue()
                                .stream()
                                .sorted(Comparator.comparing(DashboardTimelapseStationFrame::getStationId))
                                .map(this::toStationFrame)
                                .toList()
                ))
                .toList();

        return new DashboardTimelapseResponse.Detail(
                period.getPeriodKey(),
                period.getLabel(),
                period.getStartDate(),
                period.getEndDate(),
                period.getDescription(),
                period.getSource(),
                responseFrames
        );
    }

    private DashboardTimelapseResponse.Summary toSummary(DashboardTimelapsePeriod period) {
        return new DashboardTimelapseResponse.Summary(
                period.getPeriodKey(),
                period.getLabel(),
                period.getStartDate(),
                period.getEndDate(),
                period.getDescription(),
                period.getSource(),
                period.getCreatedAt(),
                period.getUpdatedAt()
        );
    }

    private DashboardTimelapseResponse.StationFrame toStationFrame(DashboardTimelapseStationFrame frame) {
        return new DashboardTimelapseResponse.StationFrame(
                frame.getStationId(),
                frame.getStationName(),
                frame.getRegion(),
                frame.getDemandKwh(),
                frame.getPvKw(),
                frame.getEssPercent(),
                frame.getTariffKrwPerKwh(),
                frame.getShareEnergyKwh(),
                frame.getActiveChargers(),
                frame.getTotalChargers(),
                frame.getVehicleCount(),
                frame.getStatus(),
                frame.getCommandText(),
                frame.getPolicyText(),
                frame.getPredictionText()
        );
    }

    private List<DashboardTimelapseStationFrame> toFrames(
            DashboardTimelapsePeriod period,
            List<DashboardTimelapseUpsertRequest.Frame> frames
    ) {
        List<DashboardTimelapseStationFrame> result = new ArrayList<>();
        for (int ordinal = 0; ordinal < frames.size(); ordinal += 1) {
            DashboardTimelapseUpsertRequest.Frame frame = frames.get(ordinal);
            int frameIndex = normalizeFrameIndex(frame.frameIndex(), ordinal);
            LocalDate frameDate = normalizeFrameDate(frame.frameDate(), period);
            int hour = normalizeHour(frame.hour());
            if (frame.stations() == null || frame.stations().isEmpty()) {
                throw new ResponseStatusException(BAD_REQUEST, "frames.stations must not be empty.");
            }
            for (DashboardTimelapseUpsertRequest.StationFrame station : frame.stations()) {
                result.add(DashboardTimelapseStationFrame.create(
                        period,
                        frameIndex,
                        frameDate,
                        hour,
                        required(station.stationId(), "station_id"),
                        required(station.stationName(), "station_name"),
                        required(station.region(), "region"),
                        required(station.demandKwh(), "demand_kwh"),
                        required(station.pvKw(), "pv_kw"),
                        required(station.essPercent(), "ess_percent"),
                        required(station.tariffKrwPerKwh(), "tariff_krw_per_kwh"),
                        station.shareEnergyKwh() == null ? 0.0 : station.shareEnergyKwh(),
                        station.activeChargers(),
                        station.totalChargers(),
                        station.vehicleCount(),
                        station.status(),
                        station.commandText(),
                        station.policyText(),
                        station.predictionText()
                ));
            }
        }
        return result;
    }

    private void validateRequest(DashboardTimelapseUpsertRequest request) {
        if (request == null) {
            throw new ResponseStatusException(BAD_REQUEST, "request body is required.");
        }
        required(request.periodKey(), "period_key");
        required(request.label(), "label");
        if (request.startDate() == null || request.endDate() == null) {
            throw new ResponseStatusException(BAD_REQUEST, "start_date and end_date are required.");
        }
        if (request.endDate().isBefore(request.startDate())) {
            throw new ResponseStatusException(BAD_REQUEST, "end_date must be on or after start_date.");
        }
        if (request.frames() == null || request.frames().isEmpty()) {
            throw new ResponseStatusException(BAD_REQUEST, "frames must not be empty.");
        }
    }

    private int normalizeHour(int hour) {
        if (hour < 0 || hour > 23) {
            throw new ResponseStatusException(BAD_REQUEST, "frame hour must be between 0 and 23.");
        }
        return hour;
    }

    private int normalizeFrameIndex(Integer frameIndex, int ordinal) {
        int resolved = frameIndex == null ? ordinal : frameIndex;
        if (resolved < 0) {
            throw new ResponseStatusException(BAD_REQUEST, "frame_index must be zero or greater.");
        }
        return resolved;
    }

    private LocalDate normalizeFrameDate(LocalDate frameDate, DashboardTimelapsePeriod period) {
        LocalDate resolved = frameDate == null ? period.getStartDate() : frameDate;
        if (resolved.isBefore(period.getStartDate()) || resolved.isAfter(period.getEndDate())) {
            throw new ResponseStatusException(BAD_REQUEST, "frame_date must be inside start_date and end_date.");
        }
        return resolved;
    }

    private String required(String value, String fieldName) {
        if (value == null || value.isBlank()) {
            throw new ResponseStatusException(BAD_REQUEST, fieldName + " is required.");
        }
        return value.trim();
    }

    private double required(Double value, String fieldName) {
        if (value == null || !Double.isFinite(value)) {
            throw new ResponseStatusException(BAD_REQUEST, fieldName + " is required.");
        }
        return value;
    }

    private List<DashboardTimelapseUpsertRequest.Frame> buildDefaultFrames() {
        List<StationSeed> stations = List.of(
                new StationSeed("1", "서울 강남 허브", "서울 강남구", 232, 92, 74, 118, -12, 12, 17),
                new StationSeed("2", "서울 마포 스테이션", "서울 마포구", 164, 76, 48, 132, 30, 9, 11),
                new StationSeed("3", "서울 송파 에너지 파크", "서울 송파구", 121, 58, 82, 96, -18, 8, 8)
        );

        List<DashboardTimelapseUpsertRequest.Frame> frames = new ArrayList<>();
        for (int hour = 0; hour < 24; hour += 1) {
            List<DashboardTimelapseUpsertRequest.StationFrame> stationFrames = new ArrayList<>();
            for (StationSeed station : stations) {
                stationFrames.add(buildStationFrame(station, hour));
            }
            frames.add(new DashboardTimelapseUpsertRequest.Frame(hour, stationFrames));
        }
        return frames;
    }

    private DashboardTimelapseUpsertRequest.StationFrame buildStationFrame(StationSeed station, int hour) {
        double daylight = daylightCurve(hour);
        double demandCurve = demandCurve(hour);
        double stationFactor = 0.92 + (Integer.parseInt(station.stationId()) % 3) * 0.07;
        double nightDrop = hour < 6 ? 0.62 : 1.0;
        double demand = Math.round(Math.max(70, station.baseDemand() * stationFactor * demandCurve * nightDrop));
        double pvPeak = Math.max(station.basePv(), 48) * 1.28 * (0.88 + (Integer.parseInt(station.stationId()) % 3) * 0.08);
        double cloudWave = 0.9 + Math.sin((hour + Integer.parseInt(station.stationId())) * 0.8) * 0.08;
        double pv = Math.round(pvPeak * daylight * cloudWave);
        double flowFactor = 0.42 + daylight * 0.54 + demandCurve * 0.24;
        double share = Math.round(station.baseShare() * flowFactor * 10.0) / 10.0;
        double ess = Math.max(25, Math.min(92, station.baseEss() + daylight * 8 - demandCurve * 11 + (station.baseShare() < 0 ? 4 : -3)));
        int activeChargers = Math.max(1, Math.min(station.totalChargers(), (int) Math.round(demand / 23.0)));
        String status = demand >= 200 ? "혼잡" : demand >= 150 ? "주의" : "정상";
        String direction = share > 0 ? "전력 수신" : share < 0 ? "전력 송신" : "공유 대기";
        return new DashboardTimelapseUpsertRequest.StationFrame(
                station.stationId(),
                station.stationName(),
                station.region(),
                demand,
                pv,
                (double) Math.round(ess),
                station.tariff(),
                share,
                activeChargers,
                station.totalChargers(),
                station.vehicleCount(),
                status,
                direction,
                String.format("%s %.1fkWh · ESS %.0f%% 유지", direction, Math.abs(share), ess),
                "EV Transformer 24시간 예측 기반 운영 프레임"
        );
    }

    private double daylightCurve(int hour) {
        if (hour < 6 || hour > 19) {
            return 0;
        }
        double normalized = (hour - 6) / 13.0;
        return Math.max(0, Math.sin(normalized * Math.PI));
    }

    private double demandCurve(int hour) {
        double morningPeak = Math.exp(-Math.pow((hour - 9) / 3.8, 2));
        double eveningPeak = Math.exp(-Math.pow((hour - 18) / 4.2, 2));
        return 0.72 + morningPeak * 0.2 + eveningPeak * 0.32;
    }

    private record StationSeed(
            String stationId,
            String stationName,
            String region,
            double baseDemand,
            double basePv,
            double baseEss,
            double tariff,
            double baseShare,
            int totalChargers,
            int vehicleCount
    ) {
    }
}
